import django_filters
from .models import ConsolidatedSession

# Allows users to filter consolidated sessions
# by organisation, programme, and date range.
class ConsolidatedSessionFilter(django_filters.FilterSet):
    organisation = django_filters.CharFilter(
        field_name='organisation',
        lookup_expr='icontains'
    )
    programme = django_filters.CharFilter(
        field_name='programme',
        lookup_expr='icontains'
    )
    session_date_from = django_filters.DateFilter(
        field_name='session_date',
        lookup_expr='gte'
    )
    session_date_to = django_filters.DateFilter(
        field_name='session_date',
        lookup_expr='lte'
    )

    class Meta:
        model = ConsolidatedSession
        fields = ['organisation', 'programme', 'session_date_from', 'session_date_to']
