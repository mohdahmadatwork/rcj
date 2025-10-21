from django.urls import path
from analytics.views import (
    CustomerAnalyticsView,
    DashboardAnalyticsView,
    CommunicationAnalyticsView,
    FullAdminAnalyticsAPIView,
    CombinedOrderAnalyticsAPIView,
    DailyOrderVolumeAPIView,
    TimeTrendsAnalyticsAPIView,
    WeeklyOrderVolumeAPIView,
    MonthlyGrowthAPIView,
    MonthlyGrowthTrendAPIView,
    CommunicationAnalyticsViewV2,
    TimelineAlertsAPIView,
    KPICardsAPIView
)

app_name = 'analytics'

urlpatterns = [
    # Main dashboard endpoint
    path('dashboard/', DashboardAnalyticsView.as_view(), name='dashboard'),
    
    # Detailed communication analytics
    # path('communication/old/', CommunicationAnalyticsView.as_view(), name='communication'),

    path('full-analysis/', FullAdminAnalyticsAPIView.as_view(), name='full-analytics'),

    path('order-analytics/', CombinedOrderAnalyticsAPIView.as_view(), name='order-analytics'),
    
    path('time-trends/', TimeTrendsAnalyticsAPIView.as_view(), name='time-trends'),
    # path('daily-order-volume/', WeeklyOrderVolumeAPIView.as_view(), name='time-trends'),
    path('monthly-growth-trend/', MonthlyGrowthAPIView.as_view(), name='time-trends'),
    
    path('daily-order-volume/', DailyOrderVolumeAPIView.as_view(), name='daily-order-volume'),
    path('monthly-order-volume/', MonthlyGrowthTrendAPIView.as_view(), name='monthly-order-volume'),
    path('timeline-alerts/', TimelineAlertsAPIView.as_view(), name='timeline-alerts'),

    path('communication/', CommunicationAnalyticsViewV2.as_view(), name='communication-analytics'),
    path('customers/', CustomerAnalyticsView.as_view(), name='customer-analytics'),

    path('kpi-cards/', KPICardsAPIView.as_view(), name='customer-analytics'),
    
]
