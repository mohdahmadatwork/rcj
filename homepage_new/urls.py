from django.urls import path
from .views import (
    CategoryListView,
    CategoryDetailView,
    WorkSampleListView,
    WorkSampleDetailView,
    WorkSampleCreateView,
    WorkSampleUpdateView,
    WorkSampleDeleteView,
    PortfolioOverviewView
)

app_name = 'portfolio'

urlpatterns = [
    # Portfolio overview endpoint (matches your frontend screen)
    path('portfolio/overview/', PortfolioOverviewView.as_view(), name='portfolio-overview'),
    
    # Category endpoints
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('categories/<slug:slug>/', CategoryDetailView.as_view(), name='category-detail'),
    
    # Work sample endpoints
    path('', WorkSampleListView.as_view(), name='work-sample-list'),
    path('create/', WorkSampleCreateView.as_view(), name='work-sample-create'),
    path('<slug:slug>/', WorkSampleDetailView.as_view(), name='work-sample-detail'),
    path('<slug:slug>/update/', WorkSampleUpdateView.as_view(), name='work-sample-update'),
    path('<slug:slug>/delete/', WorkSampleDeleteView.as_view(), name='work-sample-delete'),
]
