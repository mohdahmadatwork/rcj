# orders/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Customer APIs (require authentication)
    path('order/', views.OrderCreateView.as_view(), name='order-create'),
    path('order/status/', views.check_order_status, name='order-status'),
    path('my-orders/', views.CustomerOrderListView.as_view(), name='my-orders'),
    path('contact/', views.contact_us, name='contact-us'),
    path('my-contacts/', views.my_contact_requests, name='my-contact-requests'),
    
    # Admin APIs
    path('admin/dashboard-stats/', views.admin_dashboard_stats, name='admin-dashboard-stats'),
    path('admin/orders/', views.OrderListView.as_view(), name='admin-order-list'),
    path('admin/orders/<str:order_id>/', views.OrderAdminDetailView.as_view(), name='admin-order-detail'),
    path('admin/orders/<str:order_id>/update/', views.OrderAdminUpdateView.as_view(), name='order-update'),
    path('admin/orders/<str:order_id>/accept-decline/', views.accept_decline_order, name='order-accept-decline'),
    path('admin/orders/<str:order_id>/update-status/', views.update_order_status, name='order-update-status'),
    path('admin/orders/<str:order_id>/logs/', views.order_logs, name='order-logs'),
    path('admin/orders/create/', views.AdminOrderCreateView.as_view(), name='admin-order-create'),
    path('admin/contacts/', views.AdminContactListView.as_view(), name='admin-contact-list'),
    path('admin/contacts/<uuid:id>/', views.AdminContactUpdateView.as_view(), name='admin-contact-update')
]
