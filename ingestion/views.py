import csv
from django.http import StreamingHttpResponse
from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend

from .models import ConsolidatedSession
from .serializers import ConsolidatedSessionSerializer
from .filters import ConsolidatedSessionFilter


class SessionPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200


class ConsolidatedSessionListView(generics.ListAPIView):
    serializer_class = ConsolidatedSessionSerializer
    pagination_class = SessionPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = ConsolidatedSessionFilter

    def get_queryset(self):
        return (
            ConsolidatedSession.objects
            .prefetch_related("raw_rows")
            .order_by("session_date")
        )


class ConsolidatedSessionDetailView(generics.RetrieveAPIView):
    serializer_class = ConsolidatedSessionSerializer
    lookup_field = "normalized_session_code"
    lookup_url_kwarg = "session_code"

    def get_queryset(self):
        return (
            ConsolidatedSession.objects
            .prefetch_related("raw_rows")
        )


class SessionExportView(APIView):
    def get(self, request):
        response = StreamingHttpResponse(
            self.generate_csv(),
            content_type="text/csv"
        )
        response["Content-Disposition"] = (
            'attachment; filename="sessions_export.csv"'
        )
        return response

    def generate_csv(self):
        yield (
            "session_code,"
            "organisation,"
            "programme,"
            "facilitator,"
            "session_date,"
            "attendees\n"
        )

        queryset = ConsolidatedSession.objects.all().iterator(chunk_size=1000)

        for session in queryset:
            yield (
                f'"{session.normalized_session_code}",'
                f'"{session.organisation}",'
                f'"{session.programme}",'
                f'"{session.facilitator}",'
                f'{session.session_date},'
                f'{session.attendees}\n'
            )