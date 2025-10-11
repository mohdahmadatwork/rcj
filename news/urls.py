# news/urls.py
from django.urls import path
from .views import NewsListView,NewsDetailView,MarkNewsReadView,UnreadNewsCountView, AdminNewsListView, admin_news_targeting_options, AdminNewsCreateView, AdminNewsDetailView, admin_news_analytics, AdminNewsUpdateView

urlpatterns = [
    path('', NewsListView.as_view(), name='news-list'),
    path('<uuid:id>/', NewsDetailView.as_view(), name='news-detail'),
    path('<uuid:id>/mark-read/', MarkNewsReadView.as_view(), name='news-mark-read'),
    path('unread-count/', UnreadNewsCountView.as_view(), name='news-unread-count'),
    path('admin/', AdminNewsListView.as_view(), name='admin-news-list'),
    path('admin/targeting-options/', admin_news_targeting_options, name='admin-news-targeting-options'),
    path('admin/create/', AdminNewsCreateView.as_view(), name='admin-news-create'),
    path('admin/<uuid:id>/update/', AdminNewsUpdateView.as_view(), name='admin-news-update'),
    path('admin/<uuid:id>/', AdminNewsDetailView.as_view(), name='admin-news-detail'),
    path('admin/<uuid:id>/analytics/', admin_news_analytics, name='admin-news-analytics'),
]
