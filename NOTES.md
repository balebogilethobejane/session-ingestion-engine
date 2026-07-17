# NOTES.md

## How to Run

1. Install the project requirements.

```bash
pip install -r requirements.txt
```

2. Run the database migrations.

```bash
python manage.py migrate
```

3. Import a CSV file.

```bash
python manage.py import_sessions path/to/file.csv
```

4. Start the server.

```bash
python manage.py runserver
```

5. Run the tests.

```bash
python manage.py test
```

---

## Consolidation Rule

Sessions are matched using the `session_code` after converting it to uppercase and removing extra spaces.

If more than one row belongs to the same session, I keep the highest attendee count. I chose this because updated reports usually have the final and most accurate attendance number.

---

## Transaction and Memory Strategy

The CSV file is read one row at a time, so the whole file is never loaded into memory.

The import runs inside a database transaction. If something goes wrong, the changes are not saved, so the database stays in a good state.

The export uses `StreamingHttpResponse`, which sends the CSV a little at a time instead of loading the whole file into memory.

---

## What I Would Do With More Time

- Add more tests to cover edge cases and make sure the application continues to work as new features are added.
- Improve validation so that invalid data is caught earlier and users receive clearer error messages.
- Add a Django admin page to make it easier to view, search, and manage imported session data.
- Move large imports and exports to background tasks so users do not have to wait for long-running operations to finish.
- Add API documentation so other developers can understand and use the endpoints more easily.

---

## AI Usage

I used AI to as a learning and coding assistant throughout this assessment. I used it to help me understand the assessment requirements, break the work into smaller and more manageable tasks, explain concepts I wasn't familiar with, and answer questions whenever I got stuck.

I also used it to review parts of my code, help me think through and improve some of my test cases and explain error messages.

I want to be transparent that there were some concepts I was less familiar with. I used AI to help me understand those topics better before applying them to my project. I made the final decisions about my implementation and checked that I understood the code before using it.

I reviewed, tested, and verified all the code included in the final submission. I ran the application and the full test suite myself, made changes where needed, and confirmed that everything worked as expected before submitting.