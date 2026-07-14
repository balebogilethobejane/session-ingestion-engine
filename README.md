# Avovision Session Ingestion System

## Overview

This project imports session data from CSV files, removes duplicates, 
creates consolidated session records, and provides an API to view the data.

The system has two main data layers:

- RawSessionRow: Stores every imported row from the source file.
- ConsolidatedSession: Stores the final clean session data used by the API.

The consolidation rule is:
- Sessions are matched using the normalised session code.
- If duplicate sessions exist, the highest attendee count is kept.

---

## Setup

Clone the repository:

```bash
git clone <repo-url>
cd avovision_backend
