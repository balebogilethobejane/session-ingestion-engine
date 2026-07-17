import csv
import os
import tempfile
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.core.management import call_command
from django.urls import reverse
from .models import RawSessionRow, ConsolidatedSession
# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def make_csv(rows):
    """Write rows to a temp CSV file and return its path."""
    temp = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".csv",
        delete=False,
        newline=""
    )
    writer = csv.writer(temp)
    writer.writerow([
        "session_code",
        "organisation",
        "programme",
        "facilitator",
        "session_date",
        "attendees",
    ])
    writer.writerows(rows)
    temp.close()
    return temp.name
# ─────────────────────────────────────────────
# Import / Ingestion Tests
# ─────────────────────────────────────────────
class ImportSessionsTests(TestCase):
    def tearDown(self):
        RawSessionRow.objects.all().delete()
        ConsolidatedSession.objects.all().delete()
    def test_import_is_idempotent(self):
        """
        Importing the same file twice must not create duplicate
        RawSessionRow or ConsolidatedSession records.
        """
        csv_file = make_csv([
            ["AVO-00123", "Avovision", "Water Sec",
             "T. Mokoena", "2026-05-01", "24"],
        ])
        try:
            call_command("import_sessions", csv_file)
            call_command("import_sessions", csv_file)
            self.assertEqual(RawSessionRow.objects.count(), 1)
            self.assertEqual(ConsolidatedSession.objects.count(), 1)
        finally:
            os.remove(csv_file)
    def test_consolidation_rule_highest_attendees_wins(self):
        """
        When two raw rows share a session code (case-insensitive),
        the consolidated record must carry the highest attendee count.
        Both raw rows must be linked to the same consolidated session.
        """
        csv_file = make_csv([
            ["AVO-00123", "Avovision",  "Water Sec",
             "T. Mokoena", "2026-05-01", "24"],
            ["avo-00123", "AVOVISION",  "Water Sec",
             "T. Mokoena", "2026-05-01", "26"],
        ])
        try:
            call_command("import_sessions", csv_file)
            session = ConsolidatedSession.objects.get(
                normalized_session_code="AVO-00123"
            )
            # Conflict rule: highest attendees wins
            self.assertEqual(session.attendees, 26)
            # Both raw rows must be linked
            self.assertEqual(session.raw_rows.count(), 2)
            # Only one consolidated record must exist
            self.assertEqual(ConsolidatedSession.objects.count(), 1)
        finally:
            os.remove(csv_file)
    def test_case_insensitive_deduplication(self):
        """
        AVO-00123 and avo-00123 are the same session —
        they must produce exactly one ConsolidatedSession.
        """
        csv_file = make_csv([
            ["AVO-00123", "Avovision", "Water Sec",
             "T. Mokoena", "2026-05-01", "24"],
            ["avo-00123", "Avovision", "Water Sec",
             "T. Mokoena", "2026-05-01", "24"],
        ])
        try:
            call_command("import_sessions", csv_file)
            self.assertEqual(ConsolidatedSession.objects.count(), 1)
        finally:
            os.remove(csv_file)
    def test_missing_session_code_is_skipped(self):
        """
        A row with an empty session_code must be skipped —
        no RawSessionRow or ConsolidatedSession created.
        """
        csv_file = make_csv([
            ["", "Avovision", "Water Sec",
             "T. Mokoena", "2026-05-01", "24"],
        ])
        try:
            call_command("import_sessions", csv_file)
            self.assertEqual(RawSessionRow.objects.count(), 0)
            self.assertEqual(ConsolidatedSession.objects.count(), 0)
        finally:
            os.remove(csv_file)
    def test_missing_organisation_is_skipped(self):
        """
        A row with an empty organisation must be skipped.
        """
        csv_file = make_csv([
            ["AVO-00123", "", "Water Sec",
             "T. Mokoena", "2026-05-01", "24"],
        ])
        try:
            call_command("import_sessions", csv_file)
            self.assertEqual(RawSessionRow.objects.count(), 0)
        finally:
            os.remove(csv_file)
    def test_invalid_attendees_is_skipped(self):
        """
        A row with a non-integer attendees value must be skipped.
        """
        csv_file = make_csv([
            ["AVO-00123", "Avovision", "Water Sec",
             "T. Mokoena", "2026-05-01", "not_a_number"],
        ])
        try:
            call_command("import_sessions", csv_file)
            self.assertEqual(RawSessionRow.objects.count(), 0)
        finally:
            os.remove(csv_file)
    def test_valid_row_mixed_with_invalid_row(self):
        """
        A bad row must not block valid rows from being imported.
        The valid row must still create a record.
        """
        csv_file = make_csv([
            ["AVO-00123", "Avovision", "Water Sec",
             "T. Mokoena", "2026-05-01", "24"],
            ["", "Avovision", "Water Sec",
             "T. Mokoena", "2026-05-01", "24"],   # bad row
        ])
        try:
            call_command("import_sessions", csv_file)
            self.assertEqual(RawSessionRow.objects.count(), 1)
            self.assertEqual(ConsolidatedSession.objects.count(), 1)
        finally:
            os.remove(csv_file)
    def test_multiple_distinct_sessions(self):
        """
        Rows with different session codes must each produce
        their own ConsolidatedSession.
        """
        csv_file = make_csv([
            ["AVO-00123", "Avovision", "Water Sec",
             "T. Mokoena", "2026-05-01", "24"],
            ["GBV-00420", "GreenBiz",  "AvoConnect",
             "N. Funda",   "2026-05-03", "12"],
        ])
        try:
            call_command("import_sessions", csv_file)
            self.assertEqual(ConsolidatedSession.objects.count(), 2)
            self.assertEqual(RawSessionRow.objects.count(), 2)
        finally:
            os.remove(csv_file)
# ─────────────────────────────────────────────
# API Tests
# ─────────────────────────────────────────────
class SessionApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        """Create two sessions with raw rows once for all API tests."""
        cls.session1 = ConsolidatedSession.objects.create(
            normalized_session_code="AVO-00123",
            organisation="Avovision",
            programme="Water Sec",
            facilitator="T. Mokoena",
            session_date="2026-05-01",
            attendees=26,
        )
        RawSessionRow.objects.create(
            consolidated_session=cls.session1,
            session_code="AVO-00123",
            normalized_session_code="AVO-00123",
            organisation="Avovision",
            programme="Water Sec",
            facilitator="T. Mokoena",
            session_date="2026-05-01",
            attendees=24,
            source_file="test.csv",
            source_hash="hash001",
        )
        RawSessionRow.objects.create(
            consolidated_session=cls.session1,
            session_code="avo-00123",
            normalized_session_code="AVO-00123",
            organisation="AVOVISION",
            programme="Water Sec",
            facilitator="T. Mokoena",
            session_date="2026-05-01",
            attendees=26,
            source_file="test.csv",
            source_hash="hash002",
        )
        cls.session2 = ConsolidatedSession.objects.create(
            normalized_session_code="GBV-00420",
            organisation="GreenBiz",
            programme="AvoConnect",
            facilitator="N. Funda",
            session_date="2026-05-03",
            attendees=12,
        )
        RawSessionRow.objects.create(
            consolidated_session=cls.session2,
            session_code="GBV-00420",
            normalized_session_code="GBV-00420",
            organisation="GreenBiz",
            programme="AvoConnect",
            facilitator="N. Funda",
            session_date="2026-05-03",
            attendees=12,
            source_file="test.csv",
            source_hash="hash003",
        )
    # ── List endpoint ──────────────────────────
    def test_list_returns_200(self):
        response = self.client.get(reverse("session-list"))
        self.assertEqual(response.status_code, 200)
    def test_list_returns_all_sessions(self):
        response = self.client.get(reverse("session-list"))
        self.assertEqual(response.json()["count"], 2)
    def test_list_includes_raw_rows(self):
        """Each result must nest its raw rows."""
        response = self.client.get(reverse("session-list"))
        results = response.json()["results"]
        avo = next(r for r in results if r["normalized_session_code"] == "AVO-00123")
        self.assertEqual(len(avo["raw_rows"]), 2)
    # ── Filtering ─────────────────────────────
    def test_filter_by_organisation(self):
        response = self.client.get(
            reverse("session-list"), {"organisation": "Avovision"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(
            response.json()["results"][0]["normalized_session_code"],
            "AVO-00123"
        )
    def test_filter_by_organisation_case_insensitive(self):
        """Filter must match regardless of case."""
        response = self.client.get(
            reverse("session-list"), {"organisation": "avovision"}
        )
        self.assertEqual(response.json()["count"], 1)
    def test_filter_by_programme(self):
        response = self.client.get(
            reverse("session-list"), {"programme": "AvoConnect"}
        )
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(
            response.json()["results"][0]["normalized_session_code"],
            "GBV-00420"
        )
    def test_filter_by_date_range(self):
        response = self.client.get(
            reverse("session-list"),
            {
                "session_date_from": "2026-05-01",
                "session_date_to": "2026-05-02",
            }
        )
        self.assertEqual(response.json()["count"], 1)
        self.assertEqual(
            response.json()["results"][0]["normalized_session_code"],
            "AVO-00123"
        )
    def test_filter_no_match_returns_empty(self):
        response = self.client.get(
            reverse("session-list"), {"organisation": "NonExistent"}
        )
        self.assertEqual(response.json()["count"], 0)
    # ── N+1 guarantee ─────────────────────────
    def test_list_no_n_plus_1_queries(self):
        """
        Query count must stay fixed as session count grows.
        We expect at most 4 queries:
          1. session count (pagination)
          2. sessions fetch
          3. raw_rows prefetch
          4. optional auth/session query
        """
        with CaptureQueriesContext(connection) as ctx:
            response = self.client.get(reverse("session-list"))
            self.assertEqual(response.status_code, 200)
        self.assertLessEqual(
            len(ctx.captured_queries),
            4,
            msg=f"Expected ≤4 queries, got {len(ctx.captured_queries)}: "
                f"{[q['sql'] for q in ctx.captured_queries]}"
        )
    # ── Detail endpoint ────────────────────────
    def test_detail_returns_200(self):
        response = self.client.get(
            reverse("session-detail", kwargs={"session_code": "AVO-00123"})
        )
        self.assertEqual(response.status_code, 200)
    def test_detail_returns_correct_session(self):
        response = self.client.get(
            reverse("session-detail", kwargs={"session_code": "AVO-00123"})
        )
        data = response.json()
        self.assertEqual(data["normalized_session_code"], "AVO-00123")
        self.assertEqual(data["attendees"], 26)
    def test_detail_includes_raw_rows(self):
        response = self.client.get(
            reverse("session-detail", kwargs={"session_code": "AVO-00123"})
        )
        self.assertEqual(len(response.json()["raw_rows"]), 2)
    def test_detail_404_for_unknown_code(self):
        response = self.client.get(
            reverse("session-detail", kwargs={"session_code": "UNKNOWN-999"})
        )
        self.assertEqual(response.status_code, 404)
    # ── Export endpoint ────────────────────────
    def test_export_returns_200(self):
        response = self.client.get(reverse("session-export"))
        self.assertEqual(response.status_code, 200)
    def test_export_content_type_is_csv(self):
        response = self.client.get(reverse("session-export"))
        self.assertEqual(response["Content-Type"], "text/csv")
    def test_export_contains_header_row(self):
        response = self.client.get(reverse("session-export"))
        content = b"".join(response.streaming_content).decode("utf-8")
        self.assertIn("session_code", content)
    def test_export_contains_all_sessions(self):
        response = self.client.get(reverse("session-export"))
        content = b"".join(response.streaming_content).decode("utf-8")
        self.assertIn("AVO-00123", content)
        self.assertIn("GBV-00420", content)
