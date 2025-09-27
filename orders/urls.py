# orders/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Public APIs
    path('order/', views.OrderCreateView.as_view(), name='order-create'),
    path('order/status/', views.check_order_status, name='order-status'),
    
    # Admin APIs
    path('admin/orders/', views.OrderListView.as_view(), name='admin-order-list'),
    path('admin/orders/<str:order_id>/', views.OrderDetailView.as_view(), name='admin-order-detail'),
    path('admin/orders/<str:order_id>/accept-decline/', views.accept_decline_order, name='order-accept-decline'),
    path('admin/orders/<str:order_id>/update-status/', views.update_order_status, name='order-update-status'),
    path('admin/orders/<str:order_id>/logs/', views.order_logs, name='order-logs'),
    path('admin/orders/create/', views.AdminOrderCreateView.as_view(), name='admin-order-create'),
]
