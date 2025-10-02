# news/urls.py
from django.urls import path
from .views import NewsListView,NewsDetailView,MarkNewsReadView,UnreadNewsCountView

urlpatterns = [
    path('', NewsListView.as_view(), name='news-list'),
    path('<uuid:id>/', NewsDetailView.as_view(), name='news-detail'),
    path('<uuid:id>/mark-read/', MarkNewsReadView.as_view(), name='news-mark-read'),
    path('unread-count/', UnreadNewsCountView.as_view(), name='news-unread-count'),
]
