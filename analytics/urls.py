from django.urls import path
from analytics.views import (
    DashboardAnalyticsView,
    CommunicationAnalyticsView
)

app_name = 'analytics'

urlpatterns = [
    # Main dashboard endpoint
    path('dashboard/', DashboardAnalyticsView.as_view(), name='dashboard'),
    
    # Detailed communication analytics
    path('communication/', CommunicationAnalyticsView.as_view(), name='communication'),
]
