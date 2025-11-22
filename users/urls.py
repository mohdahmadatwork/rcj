# users/urls.py
from django.urls import path, include
from . import views

urlpatterns = [
    path('register/', views.UserRegistrationView.as_view(), name='user-register'),
    path('login/', views.user_login, name='user-login'),
    path('logout/', views.user_logout, name='user-logout'),
    path('profile/', views.UserProfileView.as_view(), name='user-profile'),
    path('dashboard/', views.customer_dashboard, name='customer-dashboard'),
    path('admin/customers/', views.AdminCustomerListView.as_view(), name='admin-customer-list'),
    path('admin/customers/lookup/', views.AdminCustomerLookupView.as_view(), name='admin-customer-lookup'),
    # path('users/create/', views.UserCreateAPIView.as_view(), name='user-create'),
    # path('users/<int:pk>/', views.UserDetailAPIView.as_view(), name='user-detail'),
    path('users/', views.UserListCreateAPIView.as_view(), name='user-list-create'),
    path('users/<int:pk>/', views.UserDetailAPIView.as_view(), name='user-detail'),
    # Add Google login
    path('google/', views.GoogleLogin.as_view(), name='google_login'),
    path('admin/users/<int:pk>/status/', views.update_user_status, name='update-user-status'),
    
    # Add dj-rest-auth URLs
    path('', include('dj_rest_auth.urls')),
    path('registration/', include('dj_rest_auth.registration.urls')),
]

