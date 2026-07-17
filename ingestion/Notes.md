# NOTES.md

## Avovision Backend Engineer Assessment

### How to run

1. Clone the repository.
2. Create and activate a virtual environment.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Apply migrations:

```bash
python manage.py migrate
```

5. Import session data:

```bash
python manage.py import_sessions <path-to-csv>
```

Example:

```bash
python manage.py import_sessions test_data.csv
```

6. Start the development server:

```bash
python manage.py runserver
```

Available endpoints:

* `GET /api/sessions/`
* `GET /api/sessions/<session_code>/`
* `GET /api/sessions/export/`

Run the test suite:

```bash
python manage.py test
```

---
## Consolidation Rule

Sessions are matched using the `session_code` after removing extra spaces and changing it to uppercase.

If more than one row belongs to the same session, only one `ConsolidatedSession` is created.

If the rows have different attendee counts, I keep the highest attendee count. I chose this because later reports are usually more complete. All original rows are still saved in `RawSessionRow` so the original data is never lost.

---

## Transaction Strategy

The import runs inside a database transaction.

Before saving a row, the data is checked to make sure it is valid.

If a row has invalid data, it is skipped and added to the import summary. The valid rows continue to be processed.

This helps prevent bad data from affecting the rest of the import.

---

## Memory Strategy

The CSV file is read one row at a time using `csv.DictReader`, so the whole file is never loaded into memory.

Rows are saved to the database in small batches instead of one at a time. This allows the system to handle large CSV files while keeping memory usage low.

---

## What I would do with another day

Given more time, I would:
1. Add better logs

I would keep a record of every import, such as:

How many rows were imported.
How many rows failed.
How long the import took.

This would make it easier to find and fix problems.

2. Improve data checking

I would add better checks before saving data.

For example:

Make sure the session code is not empty.
Make sure the attendee count is a number.
Make sure the date is in the correct format.

This would stop bad data from being saved.

3. Add more tests

I would write more tests to make sure everything works correctly.

For example:

Test importing different CSV files.
Test invalid data.
Test that the API returns the correct results.

This would help find problems before users do.

4. Improve how duplicate sessions are handled

Right now, I always keep the highest attendee count.

If I had more time, I would also look at things like:

Which record is the newest.
Which source is more reliable.

This could make the final data more accurate.

5. Use Docker

I would use Docker so that anyone can run the project in the same way on any computer.

This makes it easier for other developers to set up the project.

6. Run tests automatically

I would set up the project so that every time I upload new code, the tests run automatically.

This helps find mistakes early and makes sure new changes do not break the project.
---

## AI Usage

I used ChatGPT to help me understand the assessment requirements, break the work into smaller, manageable tasks, answer questions when I was stuck, help with debugging, and review parts of my code. I checked, tested, and understood all the code before including it in my project.
