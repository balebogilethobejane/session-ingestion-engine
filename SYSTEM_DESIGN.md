Part B – System Design
Overview

The system collects session data from an external reporting portal every three hours.

The data moves through this pipeline:

External Portal
        ↓
    Raw Data
        ↓
Consolidated Data
        ↓
  API / Users

The raw data stores the original information exactly as received. The consolidated data stores the cleaned and final version that the API uses.

Data only moves forward. The consolidated layer never changes the raw data.

1. Idempotency and Deduplication

The portal may send the same sessions every time the system checks for new data, so the system needs to prevent duplicates.

The system uses session_code as the main identifier. Before saving it, the value is cleaned by removing spaces and converting it to uppercase. This means:

AVO-00123
avo-00123

will be treated as the same session.

The system also creates a hash for each row using SHA-256. The hash helps identify if the exact same data was already imported.

If the hash already exists, the row is skipped because it is a duplicate.
If the session code exists but the hash is different, the data has changed and the system updates the consolidated record.
If the session code is new, a new consolidated session is created.

This means importing the same file multiple times will not create duplicate records.

2. Failure and Recovery

The external portal may be slow, unavailable, or send incorrect data.

To protect the system, every import runs inside a database transaction.

If something goes wrong during the import:

The changes from that import are removed.
The previous correct data stays unchanged.
The next scheduled import starts again from the beginning.

This prevents users from seeing incomplete or incorrect data.

If the portal is down or blocks requests because of too many requests, the system waits and tries again later.

Failed imports are logged and an alert is sent so the problem can be investigated.

I chose to restart failed imports instead of continuing from where they stopped because it is simpler and reduces the chance of creating inconsistent data.

3. One-Way Data Flow

The raw data and consolidated data are stored separately.

The raw data keeps the original imported information and acts as a history of what was received.

The consolidation process only reads from the raw data and creates or updates the consolidated data.

It cannot change the raw data.

This protects the original information and makes it possible to check where the final data came from.

If the system becomes larger, the raw and consolidated data could be stored in separate databases with different permissions.

4. Scaling

As the amount of data increases, the database will probably become slower.

To improve performance, I would:

Add indexes to commonly searched fields like session_code, organisation, programme, and session_date.
Process data in batches instead of one row at a time.
Use bulk inserts to reduce database operations.
Improve slow database queries.

If the system becomes much larger, I would separate data collection from data processing.

The scraper would collect data, and background workers would process it separately. This allows more data to be handled at the same time.

I would avoid adding complex solutions like database sharding or event systems too early because they make the system harder to manage.

5. Observability

The system should keep track of every import so problems can be found quickly.

For every import, the system records:

Number of rows imported
Number of duplicate rows skipped
Number of failed rows
Number of sessions created
Number of sessions updated
Time taken
Date and time of the import

These results can be compared with previous imports.

For example, if the system normally imports 500 sessions but suddenly imports 20, an alert can warn the team that something is wrong.

A dashboard showing import history would also help identify problems early.

6. Scheduling

The scraper runs automatically every three hours using a scheduler.

Before starting a new import, the system checks if another import is already running. This prevents two imports from changing the data at the same time.

If an import fails:

The error is saved in the logs.
An alert is sent.
The next scheduled import will try again automatically.


Trade-offs

The design focuses on keeping the system simple and reliable.

I chose to restart failed imports instead of continuing from where they stopped because it is easier to maintain and reduces the chance of incorrect data.

I used hashes to quickly find duplicate records while still using session_code as the main session identifier.

I separated raw and consolidated data so the original data is always available for checking.

I would not introduce technologies like Kafka or database sharding yet because the current system does not need that complexity. More advanced solutions can be added later if the system grows.