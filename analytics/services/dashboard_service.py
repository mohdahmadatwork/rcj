from django.db.models import Count, Sum, Avg, Q, F, DecimalField
from django.db.models.functions import TruncDate, Coalesce
from django.contrib.auth import get_user_model
from orders.models import Order, Message, Contact
from datetime import datetime, timedelta
from decimal import Decimal
from analytics.utils.date_utils import (
    parse_date_range, 
    get_previous_period, 
    calculate_growth_percentage
)
from analytics.utils.calculations import calculate_percentage, format_currency

User = get_user_model()


class DashboardAnalyticsService:
    """
    Main service for dashboard analytics combining all metrics.
    """
    
    def __init__(self, start_date=None, end_date=None, period=None):
        self.start_date, self.end_date = parse_date_range(start_date, end_date, period)
        self.prev_start, self.prev_end = get_previous_period(self.start_date, self.end_date)
    
    def get_complete_dashboard_data(self) -> dict:
        """
        Get all dashboard metrics in one method.
        """
        return {
            'period': self._get_period_info(),
            'overview_metrics': self._get_overview_metrics(),
            'order_status_distribution': self._get_order_status_distribution(),
            'order_trends': self._get_order_trends(),
            'recent_orders': self._get_recent_orders(),
            'deliveries_today': self._get_deliveries_today(),
            'communication_stats': self._get_communication_stats(),
            'this_month_summary': self._get_month_summary(),
            'alerts': self._get_alerts(),
        }
    
    def _get_period_info(self) -> dict:
        """Get period information."""
        return {
            'start_date': self.start_date.strftime('%Y-%m-%d'),
            'end_date': self.end_date.strftime('%Y-%m-%d'),
            'label': f"{self.start_date.strftime('%b %d')} - {self.end_date.strftime('%b %d, %Y')}"
        }
    
    def _get_overview_metrics(self) -> dict:
        """
        Get main dashboard overview metrics with growth comparison.
        """
        # Current period orders
        current_orders = Order.objects.filter(
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        )
        
        # Previous period orders for comparison
        previous_orders = Order.objects.filter(
            created_at__gte=self.prev_start,
            created_at__lte=self.prev_end
        )
        
        # Calculate metrics
        total_orders = current_orders.count()
        prev_total_orders = previous_orders.count()
        
        new_orders = current_orders.filter(order_status='new').count()
        pending_orders = current_orders.exclude(
            order_status__in=['delivered', 'declined']
        ).count()
        
        completed_orders = current_orders.filter(order_status='delivered').count()
        
        # Revenue calculations
        total_revenue = current_orders.filter(
            order_status='delivered'
        ).aggregate(
            total=Coalesce(Sum('estimated_value'), Decimal('0'))
        )['total']
        
        prev_revenue = previous_orders.filter(
            order_status='delivered'
        ).aggregate(
            total=Coalesce(Sum('estimated_value'), Decimal('0'))
        )['total']
        
        # Customer metrics
        active_customers = current_orders.values('customer').distinct().count()
        prev_active_customers = previous_orders.values('customer').distinct().count()
        
        # Average order value
        avg_order_value = current_orders.filter(
            order_status='delivered'
        ).aggregate(
            avg=Coalesce(Avg('estimated_value'), Decimal('0'))
        )['avg']
        
        prev_avg_order_value = previous_orders.filter(
            order_status='delivered'
        ).aggregate(
            avg=Coalesce(Avg('estimated_value'), Decimal('0'))
        )['avg']
        
        # Support tickets
        support_tickets = Contact.objects.filter(
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        )
        
        pending_tickets = support_tickets.filter(
            status__in=['new', 'in_progress']
        ).count()
        
        resolved_tickets = support_tickets.filter(
            status='resolved'
        ).count()
        
        return {
            'total_orders': total_orders,
            'orders_growth': calculate_growth_percentage(total_orders, prev_total_orders),
            'new_orders': new_orders,
            'pending_orders': pending_orders,
            'completed_orders': completed_orders,
            'total_revenue': format_currency(total_revenue),
            'revenue_growth': calculate_growth_percentage(
                float(total_revenue), 
                float(prev_revenue)
            ),
            'active_customers': active_customers,
            'customer_growth': calculate_growth_percentage(
                active_customers, 
                prev_active_customers
            ),
            'avg_order_value': format_currency(avg_order_value),
            'avg_order_value_growth': calculate_growth_percentage(
                float(avg_order_value), 
                float(prev_avg_order_value)
            ),
            'pending_support_tickets': pending_tickets,
            'resolved_support_tickets': resolved_tickets,
        }
    
    def _get_order_status_distribution(self) -> dict:
        """
        Get order status distribution for pie chart.
        """
        orders = Order.objects.filter(
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        )
        
        total_orders = orders.count()
        
        status_data = orders.values('order_status').annotate(
            count=Count('id'),
            total_value=Coalesce(Sum('estimated_value'), Decimal('0'))
        ).order_by('-count')
        
        distribution = []
        for item in status_data:
            distribution.append({
                'status': item['order_status'],
                'status_display': dict(Order.ORDER_STATUS_CHOICES).get(
                    item['order_status'], 
                    item['order_status']
                ),
                'count': item['count'],
                'percentage': calculate_percentage(item['count'], total_orders),
                'total_value': format_currency(item['total_value'])
            })
        
        return {
            'total_orders': total_orders,
            'distribution': distribution
        }
    
    def _get_order_trends(self) -> dict:
        """
        Get order trends for the last 7 days for the chart.
        """
        # Get last 7 days from end_date
        seven_days_ago = self.end_date - timedelta(days=6)
        
        # Aggregate orders by date
        daily_orders = Order.objects.filter(
            created_at__gte=seven_days_ago,
            created_at__lte=self.end_date
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        # Create a complete date range
        date_map = {item['date']: item['count'] for item in daily_orders}
        
        trends = []
        current_date = seven_days_ago.date()
        end = self.end_date.date()
        
        while current_date <= end:
            trends.append({
                'date': current_date.strftime('%b %d'),
                'orders': date_map.get(current_date, 0)
            })
            current_date += timedelta(days=1)
        
        return {
            'period': 'Last 7 Days',
            'data': trends
        }
    
    def _get_recent_orders(self, limit=6) -> list:
        """
        Get recent orders for the dashboard.
        """
        orders = Order.objects.filter(
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        ).select_related('customer').order_by('-created_at')[:limit]
        
        result = []
        for order in orders:
            result.append({
                'order_id': order.order_id,
                'customer_name': order.full_name,
                'customer_email': order.customer.email if order.customer else order.email,
                'status': order.order_status,
                'status_display': order.get_order_status_display(),
                'created_at': order.created_at.strftime('%d %b %Y')
            })
        
        return result
    
    def _get_deliveries_today(self) -> dict:
        """
        Get deliveries scheduled for today.
        """
        from django.utils import timezone
        today = timezone.now().date()
        
        deliveries = Order.objects.filter(
            preferred_delivery_date=today,
            order_status__in=['ready', 'delivered']
        ).select_related('customer')
        
        count = deliveries.count()
        
        delivery_list = []
        for order in deliveries:
            delivery_list.append({
                'order_id': order.order_id,
                'customer_name': order.full_name,
                'status': order.order_status,
                'status_display': order.get_order_status_display()
            })
        
        return {
            'count': count,
            'deliveries': delivery_list
        }
    
    def _get_communication_stats(self) -> dict:
        """
        Get communication statistics:
        - Messages from order detail page
        - Contact form submissions
        - Authenticated vs non-authenticated contacts
        """
        # Messages in order details
        order_messages = Message.objects.filter(
            created_at__gte=self.start_date,
            created_at__lte=self.end_date,
            order__isnull=False  # Only order-related messages
        )
        
        total_order_messages = order_messages.count()
        user_messages = order_messages.filter(sender_type='user').count()
        admin_messages = order_messages.filter(sender_type='admin').count()
        system_messages = order_messages.filter(sender_type='system').count()
        
        # Unique customers who contacted via messages
        customers_via_messages = order_messages.filter(
            sender_type='user'
        ).values('sender').distinct().count()
        
        # Contact form submissions
        contacts = Contact.objects.filter(
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        )
        
        total_contacts = contacts.count()
        
        # Authenticated users who contacted
        authenticated_contacts = contacts.filter(
            user__isnull=False
        ).count()
        
        # Non-authenticated contacts
        guest_contacts = contacts.filter(
            user__isnull=True
        ).count()
        
        # Order-related vs general contacts
        order_related_contacts = contacts.filter(order_related=True).count()
        general_contacts = contacts.filter(order_related=False).count()
        
        # Contact status breakdown
        contact_status = contacts.values('status').annotate(
            count=Count('id')
        )
        
        status_breakdown = {
            item['status']: item['count'] for item in contact_status
        }
        
        return {
            'order_messages': {
                'total': total_order_messages,
                'by_sender': {
                    'user': user_messages,
                    'admin': admin_messages,
                    'system': system_messages
                },
                'unique_customers_contacted': customers_via_messages
            },
            'contact_form': {
                'total': total_contacts,
                'authenticated_users': authenticated_contacts,
                'guest_users': guest_contacts,
                'order_related': order_related_contacts,
                'general_inquiries': general_contacts,
                'status_breakdown': status_breakdown
            },
            'total_communications': total_order_messages + total_contacts
        }
    
    def _get_month_summary(self) -> dict:
        """
        Get current month summary metrics.
        """
        from django.utils import timezone
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Orders this month
        month_orders = Order.objects.filter(
            created_at__gte=month_start,
            created_at__lte=now
        )
        
        active_orders = month_orders.exclude(
            order_status__in=['delivered', 'declined']
        ).count()
        
        completed_orders = month_orders.filter(order_status='delivered').count()
        total_month_orders = month_orders.count()
        
        # Completion rate
        completion_rate = calculate_percentage(completed_orders, total_month_orders)
        
        # Revenue
        revenue = month_orders.filter(
            order_status='delivered'
        ).aggregate(
            total=Coalesce(Sum('estimated_value'), Decimal('0'))
        )['total']
        
        # Target (you can make this configurable)
        revenue_target = Decimal('500000.00')
        revenue_percentage = calculate_percentage(
            float(revenue), 
            float(revenue_target)
        )
        
        return {
            'order_completion_rate': completion_rate,
            'active_orders': active_orders,
            'revenue_target': format_currency(revenue_target),
            'revenue_achieved': format_currency(revenue),
            'revenue_percentage': revenue_percentage
        }
    
    def _get_alerts(self) -> list:
        """
        Get important alerts for the dashboard.
        """
        alerts = []
        
        # New orders requiring attention
        new_orders = Order.objects.filter(
            order_status='new',
            created_at__gte=self.start_date,
            created_at__lte=self.end_date
        ).count()
        
        if new_orders > 0:
            alerts.append({
                'type': 'warning',
                'title': f'{new_orders} new order(s) received',
                'message': 'Requires attention',
                'priority': 'high'
            })
        
        # Pending support tickets
        pending_tickets = Contact.objects.filter(
            status__in=['new', 'in_progress']
        ).count()
        
        if pending_tickets > 0:
            alerts.append({
                'type': 'info',
                'title': f'{pending_tickets} support ticket(s) pending',
                'message': 'Awaiting response',
                'priority': 'medium'
            })
        
        # Overdue deliveries
        from django.utils import timezone
        today = timezone.now().date()
        overdue = Order.objects.filter(
            preferred_delivery_date__lt=today,
            order_status__in=['confirmed', 'cad_done', 'user_confirmed', 'rpt_done', 'casting', 'ready']
        ).count()
        
        if overdue > 0:
            alerts.append({
                'type': 'error',
                'title': f'{overdue} order(s) overdue',
                'message': 'Delivery date passed',
                'priority': 'high'
            })
        
        return alerts
