# users/urls.py
from django.urls import path, include
from . import views

urlpatterns = [
    path('register/', views.UserRegistrationView.as_view(), name='user-register'),
    path('login/', views.user_login, name='user-login'),
    path('logout/', views.user_logout, name='user-logout'),
    path('profile/', views.UserProfileView.as_view(), name='user-profile'),
    path('dashboard/', views.customer_dashboard, name='customer-dashboard'),
     # Add Google login
    path('google/', views.GoogleLogin.as_view(), name='google_login'),
    
    # Add dj-rest-auth URLs
    path('', include('dj_rest_auth.urls')),
    path('registration/', include('dj_rest_auth.registration.urls')),
]
