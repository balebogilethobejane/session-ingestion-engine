from django.db import models

# Stores every imported row exactly as it appeared in the source file.
# This provides an audit trail and allows the original data to be traced.
class RawSessionRow(models.Model):
    
  
    # Links each raw row to its consolidated session.
    consolidated_session = models.ForeignKey(
        'ConsolidatedSession',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='raw_rows' 
    )
    
    session_code = models.CharField(max_length=50)
    normalized_session_code = models.CharField(max_length=50)
    organisation = models.CharField(max_length=255)
    programme = models.CharField(max_length=255)
    facilitator = models.CharField(max_length=255)
    session_date = models.DateField()
    attendees = models.PositiveIntegerField()
    source_file = models.CharField(max_length=255)
    source_hash = models.CharField(max_length=64, unique=True)
    imported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Indexes make searching and filtering faster.
        indexes = [
            models.Index(fields=["normalized_session_code"]),
            models.Index(fields=["organisation"]),
            models.Index(fields=["programme"]),
            models.Index(fields=["session_date"]),
            models.Index(fields=["source_file"]),
        ]

# Stores the final version of each session after duplicate rows
# have been combined.
class ConsolidatedSession(models.Model):


    # The session code is normalised so duplicates with different
    # casing are treated as the same session.
    normalized_session_code = models.CharField(max_length=50, unique=True)
    organisation = models.CharField(max_length=255)
    programme = models.CharField(max_length=255)
    facilitator = models.CharField(max_length=255)
    session_date = models.DateField()
    attendees = models.PositiveIntegerField()
    
    # Updated automatically whenever the session changes
    last_updated = models.DateTimeField(auto_now=True) 
    
    # Tracks how many raw rows belong to this session.
    raw_rows_count = models.IntegerField(default=1)
    
    class Meta:
        indexes = [
            models.Index(fields=["normalized_session_code"]),
            models.Index(fields=["organisation"]),
            models.Index(fields=["programme"]),
            models.Index(fields=["session_date"]),
        ]

