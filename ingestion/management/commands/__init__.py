import csv
import hashlib
from django.core.management.base import BaseCommand
from django.db import transaction
from ingestion.models import RawSessionRow, ConsolidatedSession


class Command(BaseCommand):
    help = "Import training sessions from a CSV file with idempotent processing"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str, help="Path to the CSV file to import")

    def handle(self, *args, **options):
        csv_file = options["csv_file"]
        
        try:
            stats = self.import_sessions(csv_file)
            self.print_summary(stats)
        except FileNotFoundError:
            self.stderr.write(f"Error: File '{csv_file}' not found")
        except Exception as e:
            self.stderr.write(f"Unexpected error: {e}")

    @transaction.atomic
    def import_sessions(self, csv_file):
        """Main import method with transaction wrapping the entire process"""
        self.stdout.write(f"Starting import of {csv_file}")
        
        stats = {
            'rows_processed': 0,
            'rows_skipped': 0,
            'sessions_created': 0,
            'sessions_updated': 0,
            'errors': []
        }
        
        try:
            with open(csv_file, newline="", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                
                # Process in batches for memory efficiency
                batch_size = 100
                raw_batch = []
                consolidated_updates = []
                
                for row_num, row in enumerate(reader, start=1):
                    try:
                        processed = self.process_row(row, csv_file, stats)
                        if processed:
                            raw_batch.append(processed['raw_data'])
                            consolidated_updates.append(processed['consolidation_data'])
                            
                            # Process batch when full
                            if len(raw_batch) >= batch_size:
                                self.process_batch(raw_batch, consolidated_updates, stats)
                                raw_batch = []
                                consolidated_updates = []
                                
                    except Exception as e:
                        stats['errors'].append(f"Row {row_num}: {str(e)}")
                        stats['rows_skipped'] += 1
                
                # Process remaining rows in final batch
                if raw_batch:
                    self.process_batch(raw_batch, consolidated_updates, stats)
                    
        except csv.Error as e:
            stats['errors'].append(f"CSV parsing error: {e}")
            raise
        except Exception as e:
            stats['errors'].append(f"File reading error: {e}")
            raise
            
        return stats

    def process_row(self, row, source_file, stats):
        """Process a single CSV row and prepare data for batch processing"""
        # Validate required fields
        required_fields = ['session_code', 'organisation', 'programme', 
                          'facilitator', 'session_date', 'attendees']
        
        for field in required_fields:
            if field not in row or not str(row[field]).strip():
                raise ValueError(f"Missing or empty required field: {field}")
        
        # Generate unique hash for idempotency
        row_content = ''.join(str(row[field]) for field in sorted(row.keys()))
        row_hash = hashlib.sha256(row_content.encode('utf-8')).hexdigest()
        
        # Check if already imported (idempotency)
        if RawSessionRow.objects.filter(source_hash=row_hash).exists():
            stats['rows_skipped'] += 1
            return None
        
        # Normalize session code (case-insensitive, trimmed)
        normalized_code = row['session_code'].strip().upper()
        
        # Validate attendees is an integer
        try:
            attendees = int(row['attendees'])
            if attendees < 0:
                raise ValueError("Attendees cannot be negative")
        except ValueError:
            raise ValueError(f"Invalid attendees value: {row['attendees']}")
        
        # Prepare raw row data
        raw_data = {
            'session_code': row['session_code'],
            'normalized_session_code': normalized_code,
            'organisation': row['organisation'],
            'programme': row['programme'],
            'facilitator': row['facilitator'],
            'session_date': row['session_date'],
            'attendees': attendees,
            'source_file': source_file,
            'source_hash': row_hash,
        }
        
        # Prepare consolidation data
        consolidation_data = {
            'normalized_session_code': normalized_code,
            'organisation': row['organisation'],
            'programme': row['programme'],
            'facilitator': row['facilitator'],
            'session_date': row['session_date'],
            'attendees': attendees,
        }
        
        return {
            'raw_data': raw_data,
            'consolidation_data': consolidation_data
        }

    def process_batch(self, raw_batch, consolidation_batch, stats):
        """Process a batch of rows in a single database operation"""
        if not raw_batch:
            return
        
        # Create raw session rows using bulk_create
        raw_objects = [RawSessionRow(**data) for data in raw_batch]
        RawSessionRow.objects.bulk_create(raw_objects)
        stats['rows_processed'] += len(raw_batch)
        
        # Process consolidation for each session
        for data in consolidation_batch:
            self.consolidate_session(data, stats)

    def consolidate_session(self, session_data, stats):
        """Consolidate session data with conflict resolution"""
        normalized_code = session_data['normalized_session_code']
        
        try:
            # Try to get existing consolidated session
            existing = ConsolidatedSession.objects.get(
                normalized_session_code=normalized_code
            )
            
            # Conflict resolution: choose highest attendee count
            if session_data['attendees'] > existing.attendees:
                existing.attendees = session_data['attendees']
                existing.save()
                stats['sessions_updated'] += 1
                
        except ConsolidatedSession.DoesNotExist:
            # Create new consolidated session
            consolidated_data = {
                'session_code': normalized_code,
                **session_data
            }
            ConsolidatedSession.objects.create(**consolidated_data)
            stats['sessions_created'] += 1

    def print_summary(self, stats):
        """Print detailed import summary"""
        self.stdout.write("\n" + "="*50)
        self.stdout.write("IMPORT SUMMARY")
        self.stdout.write("="*50)
        
        self.stdout.write(f"Rows processed: {stats['rows_processed']}")
        self.stdout.write(f"Rows skipped (duplicates): {stats['rows_skipped']}")
        self.stdout.write(f"Sessions created: {stats['sessions_created']}")
        self.stdout.write(f"Sessions updated: {stats['sessions_updated']}")
        
        if stats['errors']:
            self.stdout.write(f"\nErrors encountered: {len(stats['errors'])}")
            for error in stats['errors'][:10]:  # Show first 10 errors only
                self.stdout.write(f"  • {error}")
            if len(stats['errors']) > 10:
                self.stdout.write(f"  ... and {len(stats['errors']) - 10} more errors")
        else:
            self.stdout.write(self.style.SUCCESS("\nImport completed with no errors!"))
        
        self.stdout.write("="*50)
