from django.urls import path
from .views import (
    ConsolidatedSessionListView,
    ConsolidatedSessionDetailView,
    SessionExportView,
)

urlpatterns = [
    path('sessions/', ConsolidatedSessionListView.as_view(), name='session-list'),
    path('sessions/export/', SessionExportView.as_view(), name='session-export'),
    path('sessions/<str:session_code>/', ConsolidatedSessionDetailView.as_view(), name='session-detail'),
]

