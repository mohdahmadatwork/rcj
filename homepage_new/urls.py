from django.urls import path
from .views import (
    CategoryListView,
    CategoryDetailView,
    WorkSampleListView,
    WorkSampleDetailView,
    WorkSampleCreateView,
    WorkSampleUpdateView,
    WorkSampleDeleteView,
    PortfolioOverviewView,
    PublicWorkSampleListView
)


app_name = 'portfolio'


urlpatterns = [
    # Portfolio overview endpoint (matches your frontend screen)
    path('portfolio/overview/', PortfolioOverviewView.as_view(), name='portfolio-overview'),
    
    # Category endpoints
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('categories/<int:pk>/', CategoryDetailView.as_view(), name='category-detail'),
    
    # Work sample endpoints (ID-based)
    path('', WorkSampleListView.as_view(), name='work-sample-list'),
    path('create/', WorkSampleCreateView.as_view(), name='work-sample-create'),
    path('<int:pk>/', WorkSampleDetailView.as_view(), name='work-sample-detail'),
    path('<int:pk>/update/', WorkSampleUpdateView.as_view(), name='work-sample-update'),
    path('<int:pk>/delete/', WorkSampleDeleteView.as_view(), name='work-sample-delete'),

    path('public/', PublicWorkSampleListView.as_view(), name='public-work-sample-list')
]
