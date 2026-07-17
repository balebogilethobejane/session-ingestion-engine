Part B – System Design
Overview

The system will collect session data from an external reporting portal every three hours. The data moves through a simple pipeline:

External Portal
        ↓
   Raw Data
        ↓
Consolidated Data
        ↓
 API / Consumers

Each stage only passes data forward. The raw data is kept as the original record, while the consolidated data is the cleaned version that the API and reports use.

1. Idempotency and Deduplication

The portal may send the same sessions every time it is scraped, so the system needs to avoid creating duplicates.

The session_code is used as the unique identifier after it has been normalised (trimmed and converted to uppercase). This allows AVO-00123 and avo-00123 to be treated as the same session.

To quickly detect identical rows, each row is also hashed using SHA-256 after it has been parsed. If the hash already exists, the row is identical to one that has already been processed, so it is skipped.

If the session_code already exists but the hash is different, it means something has changed, such as the attendee count. The system treats this as a genuine update and applies the consolidation rule, where the highest attendee count is kept.

This approach makes the import idempotent because importing the same data multiple times does not create duplicate records.

2. Failure and Recovery

The external portal may be slow, unavailable, or return invalid data, so the system should recover safely when something goes wrong.

The import is processed in batches, with each batch running inside its own database transaction. If a batch fails, only that batch is rolled back while previously completed batches remain unchanged.

If the import cannot finish successfully, the data from the failed import is discarded and the next scheduled run starts again from the beginning. The existing consolidated data is never replaced until the entire import has completed successfully.

This means users will never see partially imported data.

If the portal is temporarily unavailable or rate-limits requests, the system waits before retrying instead of continuously sending requests. Failed imports are logged and an alert is generated so the issue can be investigated.

I chose to restart failed imports rather than trying to continue from where they stopped because it is simpler, easier to maintain, and reduces the chance of introducing inconsistent data.

3. One-Way Data Flow

The raw data and consolidated data are kept separate.

The raw data acts as an audit trail and stores the original information exactly as it was received. The consolidation process only reads from the raw data and creates or updates records in the consolidated table.

The consolidation process never writes back to the raw data. This protects the original data from accidental changes and ensures there is always a reliable copy of what was originally imported.

If the system grows in the future, the raw and consolidated data could even be stored in separate databases, with the consolidation service only having read access to the raw database.

4. Scaling

As the system grows and more session data is imported, the database may start to slow down.

To improve performance, I would:

Add indexes to fields that are searched often, such as session_code, organisation, programme, and session_date.
Process data in batches instead of one row at a time.
Use bulk inserts and updates to reduce the number of database operations.
Optimise database queries to avoid unnecessary database calls.

If the system becomes much larger, I would separate the data collection from the data processing. This would allow the scraper to keep collecting data while other workers process it in the background, making the system faster and easier to scale.

I would avoid introducing more complex solutions, such as database sharding or event sourcing, until they are actually needed. Starting with a simpler design makes the system easier to maintain and debug.

5. Observability

The system should record information about every import so that problems can be detected early.

For every import, I would log:

Number of rows imported
Number of duplicate rows skipped
Number of failed rows
Number of sessions created
Number of sessions updated
Time taken to complete the import
Date and time of the import

These values can be compared with previous imports. If today's import suddenly contains far fewer sessions than normal, or an import fails completely, the system should send an alert so that someone can investigate.

A simple dashboard showing import history would also make it easier to identify trends or recurring problems before they become serious.

6. Scheduling

The scraper runs automatically every three hours using a scheduler such as a cron job or Celery Beat.

Before a new import starts, the system checks whether another import is already running. If one is still running, the new import is skipped and a warning is logged. This prevents two imports from running at the same time and updating the same data.

If an import fails, an alert is sent immediately, and the next scheduled run automatically retries the import.

Trade-offs

I made a few design decisions to keep the system reliable without making it unnecessarily complex.

I chose to restart failed imports instead of trying to resume them because it is simpler and reduces the risk of processing incomplete data.
I used row hashes to quickly detect identical records while still using the normalised session_code as the main identifier for sessions.
I kept the raw and consolidated data separate so the original data always remains available for auditing.
I would not introduce technologies such as Kafka or database sharding at this stage because the system does not yet require that level of complexity. It is better to keep the design simple and only add complexity when there is a clear need.