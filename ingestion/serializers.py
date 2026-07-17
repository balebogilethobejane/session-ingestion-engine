from rest_framework import serializers
from .models import RawSessionRow, ConsolidatedSession

# Serializes raw session rows so they can be returned by the API.
class RawSessionRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = RawSessionRow
        fields = [
            'id',
            'session_code',
            'normalized_session_code',
            'organisation',
            'programme',
            'facilitator',
            'session_date',
            'attendees',
            'source_file',
            'imported_at',
        ]

# Serializes the consolidated session and includes all related
# raw rows for auditing and traceability.
class ConsolidatedSessionSerializer(serializers.ModelSerializer):

    # Include all raw rows linked to the consolidated session.
    raw_rows = RawSessionRowSerializer(many=True, read_only=True)

    class Meta:
        model = ConsolidatedSession
        fields = [
            'id',
            'normalized_session_code',
            'organisation',
            'programme',
            'facilitator',
            'session_date',
            'attendees',
            'last_updated',
            'raw_rows',
        ]
