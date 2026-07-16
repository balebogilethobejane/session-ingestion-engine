from django.db import models

class RawSessionRow(models.Model):
    # Original data fields
    session_code = models.CharField(max_length=50)
    organisation = models.CharField(max_length=255)
    programme = models.CharField(max_length=255)
    facilitator = models.CharField(max_length=255)
    session_date = models.DateField()
    attendees = models.PositiveIntegerField()
    source_file = models.CharField(max_length=255)
    
    # System fields
    normalized_session_code = models.CharField(max_length=50)
    imported_at = models.DateTimeField(auto_now_add=True)
    source_hash = models.CharField(max_length=64, unique=True)
    
    class Meta:
        indexes = [
            models.Index(fields=["normalized_session_code"]),
            models.Index(fields=["organisation"]),
            models.Index(fields=["programme"]),
            models.Index(fields=["session_date"]),
            models.Index(fields=["source_file"]),
        ]

class ConsolidatedSession(models.Model):
    # Canonical data
    normalized_session_code = models.CharField(max_length=50, unique=True)
    organisation = models.CharField(max_length=255)
    programme = models.CharField(max_length=255)
    facilitator = models.CharField(max_length=255)
    session_date = models.DateField()
    attendees = models.PositiveIntegerField()
    
    # System fields
    last_updated = models.DateTimeField(auto_now=True)
    raw_rows_count = models.IntegerField(default=1)
    
    class Meta:
        indexes = [
            models.Index(fields=["normalized_session_code"]),
            models.Index(fields=["organisation"]),
            models.Index(fields=["programme"]),
            models.Index(fields=["session_date"]),
        ]

