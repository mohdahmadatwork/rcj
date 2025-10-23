from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from analytics.services.dashboard_service import DashboardAnalyticsService
from analytics.serializers import (
    DashboardAnalyticsSerializer, 
    DateRangeInputSerializer
)
from django.contrib.auth import get_user_model

def is_admin_user(user):
    """Helper function to check if user is admin"""
    return user.is_authenticated and hasattr(user, 'user_type') and user.user_type.lower() == 'admin'

User = get_user_model()
class DashboardAnalyticsView(APIView):
    """
    API endpoint for complete dashboard analytics.
    
    Returns all metrics needed for the dashboard including:
    - Overview metrics (orders, revenue, customers)
    - Order status distribution
    - Order trends (last 7 days)
    - Recent orders
    - Today's deliveries
    - Communication statistics (messages & contacts)
    - Monthly summary
    - Alerts
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        Get dashboard analytics data.
        
        Query Parameters:
        - start_date (optional): Start date in YYYY-MM-DD format
        - end_date (optional): End date in YYYY-MM-DD format
        - period (optional): 'today', 'week', 'month', 'quarter', 'year'
        
        If no parameters provided, defaults to last 30 days.
        """
        # Validate input
        input_serializer = DateRangeInputSerializer(data=request.query_params)
        
        if not input_serializer.is_valid():
            return Response(
                {
                    'success': False,
                    'errors': input_serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        validated_data = input_serializer.validated_data
        
        # Get analytics data
        service = DashboardAnalyticsService(
            start_date=validated_data.get('start_date'),
            end_date=validated_data.get('end_date'),
            period=validated_data.get('period')
        )
        
        try:
            data = service.get_complete_dashboard_data()
            
            return Response({
                'success': True,
                'data': data,
                'meta': {
                    'timestamp': request._request.META.get('HTTP_DATE'),
                    'user': request.user.username
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {
                    'success': False,
                    'error': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CommunicationAnalyticsView(APIView):
    """
    Detailed communication analytics endpoint.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get detailed communication statistics."""
        input_serializer = DateRangeInputSerializer(data=request.query_params)
        
        if not input_serializer.is_valid():
            return Response(
                {'success': False, 'errors': input_serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        validated_data = input_serializer.validated_data
        
        service = DashboardAnalyticsService(
            start_date=validated_data.get('start_date'),
            end_date=validated_data.get('end_date'),
            period=validated_data.get('period')
        )
        
        try:
            data = service._get_communication_stats()
            
            return Response({
                'success': True,
                'data': data
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# analytics/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from .servicesv2 import AdminAnalyticsService
from .serializers import AnalyticsDashboardResponseSerializer


class FullAdminAnalyticsAPIView(APIView):
    """
    GET /api/admin/analytics/full-analysis
    
    Query Parameters:
    - time_filter: 'today' | 'week' | 'month' | 'quarter' | 'year'
    - start_date: YYYY-MM-DD
    - end_date: YYYY-MM-DD
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get query parameters
        query_params = {
            'time_filter': request.query_params.get('time_filter'),
            'start_date': request.query_params.get('start_date'),
            'end_date': request.query_params.get('end_date'),
        }
        
        # Get analytics data from service
        service = AdminAnalyticsService()
        analytics_data = service.get_full_analysis(query_params)
        
        # Serialize and return
        serializer = AnalyticsDashboardResponseSerializer(analytics_data)
        return Response(serializer.data)

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Avg, F, ExpressionWrapper, DurationField
from django.utils import timezone
from datetime import timedelta, datetime
from orders.models import Order
from auditlog.models import LogEntry
from django.contrib.contenttypes.models import ContentType


class OrderStatusDistributionAPIView(APIView):
    """
    GET /api/admin/analytics/order-status-distribution
    
    Returns order status distribution with counts and percentages
    
    Query Parameters:
    - start_date: Filter orders created after this date (format: YYYY-MM-DD)
    - end_date: Filter orders created before this date (format: YYYY-MM-DD)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Get date filters from query parameters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # Build base queryset
        queryset = Order.objects.all()
        
        # Apply date filters if provided
        if start_date:
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                queryset = queryset.filter(created_at__gte=start_date_obj)
            except ValueError:
                return Response({
                    'error': 'Invalid start_date format. Use YYYY-MM-DD'
                }, status=400)
        
        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                # Add one day to include the entire end_date
                end_date_obj = datetime.combine(end_date_obj, datetime.max.time())
                queryset = queryset.filter(created_at__lte=end_date_obj)
            except ValueError:
                return Response({
                    'error': 'Invalid end_date format. Use YYYY-MM-DD'
                }, status=400)
        
        # Define status groupings
        in_progress_statuses = ['confirmed', 'cad_done', 'user_confirmed', 'rpt_done', 'casting', 'ready']
        
        # Get total orders count
        total_orders = queryset.count()
        
        # Count orders by grouped statuses
        delivered_count = queryset.filter(order_status='delivered').count()
        in_progress_count = queryset.filter(order_status__in=in_progress_statuses).count()
        new_count = queryset.filter(order_status='new').count()
        declined_count = queryset.filter(order_status='declined').count()
        cad_done = queryset.filter(order_status='cad_done').count()
        
        # Calculate percentages (handle division by zero)
        def calculate_percentage(count, total):
            return round((count / total) * 100, 1) if total > 0 else 0.0
        
        # Always return data structure even if no orders
        data = [
            {
                'status': 'Delivered',
                'count': delivered_count,
                'percentage': calculate_percentage(delivered_count, total_orders),
                'color': 'bg-blue-500'
            },
            {
                'status': 'In Progress',
                'count': in_progress_count,
                'percentage': calculate_percentage(in_progress_count, total_orders),
                'color': 'bg-yellow-500'
            },
            {
                'status': 'New',
                'count': new_count,
                'percentage': calculate_percentage(new_count, total_orders),
                'color': 'bg-purple-500'
            },
            {
                'status': 'Declined',
                'count': declined_count,
                'percentage': calculate_percentage(declined_count, total_orders),
                'color': 'bg-red-500'
            }
        ]
        
        return Response({
            'status_distribution': data,
            'total_orders': total_orders,
            'cad_done': cad_done,
            'declined': declined_count,
            'filters': {
                'start_date': start_date,
                'end_date': end_date
            }
        })


class StagePerformanceAPIView(APIView):
    """
    GET /api/admin/analytics/stage-performance
    
    Returns average time spent in each order stage using AuditLog
    
    Query Parameters:
    - start_date: Filter orders created after this date (format: YYYY-MM-DD)
    - end_date: Filter orders created before this date (format: YYYY-MM-DD)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Get date filters from query parameters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # Validate date formats
        if start_date:
            try:
                datetime.strptime(start_date, '%Y-%m-%d')
            except ValueError:
                return Response({
                    'error': 'Invalid start_date format. Use YYYY-MM-DD'
                }, status=400)
        
        if end_date:
            try:
                datetime.strptime(end_date, '%Y-%m-%d')
            except ValueError:
                return Response({
                    'error': 'Invalid end_date format. Use YYYY-MM-DD'
                }, status=400)
        
        stage_performance = []
        
        # Define stage transitions
        stage_transitions = [
            {'from': 'new', 'to': 'confirmed', 'name': 'New → Confirmed', 'threshold': 3},
            {'from': 'confirmed', 'to': 'cad_done', 'name': 'CAD Design', 'threshold': 4},
            {'from': 'cad_done', 'to': 'user_confirmed', 'name': 'User Confirmation', 'threshold': 2},
            {'from': 'user_confirmed', 'to': 'rpt_done', 'name': 'RPT Done', 'threshold': 3},
            {'from': 'rpt_done', 'to': 'casting', 'name': 'Casting', 'threshold': 4},
            {'from': 'ready', 'to': 'delivered', 'name': 'Ready → Delivered', 'threshold': 2},
        ]
        
        for transition in stage_transitions:
            avg_time = self._calculate_stage_time_from_auditlog(
                transition['from'], 
                transition['to'],
                start_date,
                end_date
            )
            
            stage_performance.append({
                'stage': transition['name'],
                'avgTime': avg_time['label'],
                'avgDays': avg_time['days'],
                'icon': 'AlertCircle' if avg_time['status'] == 'warning' else 'Clock',
                'status': self._get_status(avg_time['days'], transition['threshold'])
            })
        
        return Response({
            'stage_performance': stage_performance,
            'total_stages': len(stage_performance),
            'filters': {
                'start_date': start_date,
                'end_date': end_date
            }
        })
    
    def _calculate_stage_time_from_auditlog(self, from_status, to_status, start_date=None, end_date=None):
        """
        Calculate average time between two statuses using AuditLog
        
        This method looks at the audit log to find when orders transitioned
        from one status to another and calculates the average time.
        """
        # Get Order content type for auditlog filtering
        order_content_type = ContentType.objects.get_for_model(Order)
        
        # Build base queryset for orders
        orders_queryset = Order.objects.all()
        
        # Apply date filters if provided
        if start_date:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            orders_queryset = orders_queryset.filter(created_at__gte=start_date_obj)
        
        if end_date:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            end_date_obj = datetime.combine(end_date_obj, datetime.max.time())
            orders_queryset = orders_queryset.filter(created_at__lte=end_date_obj)
        
        # Get all orders that have reached the 'to' status
        orders_with_target_status = orders_queryset.filter(
            order_status=to_status
        ) | orders_queryset.filter(
            # Also include orders that have moved past this status
            order_status__in=self._get_statuses_after(to_status)
        )
        
        time_differences = []
        
        for order in orders_with_target_status:
            # Get audit logs for this specific order
            order_logs = LogEntry.objects.filter(
                content_type=order_content_type,
                object_pk=str(order.pk)
            ).order_by('timestamp')
            
            from_timestamp = None
            to_timestamp = None
            
            # Find the timestamps for status transitions
            for log in order_logs:
                if log.changes:
                    # Check if order_status changed
                    changes_dict = log.changes
                    if 'order_status' in changes_dict:
                        old_status, new_status = changes_dict['order_status']
                        
                        # When order moves FROM the from_status
                        if old_status == from_status:
                            from_timestamp = log.timestamp
                        
                        # When order moves TO the to_status
                        if new_status == to_status:
                            to_timestamp = log.timestamp
                            
                            # If we have both timestamps, calculate difference
                            if from_timestamp and to_timestamp:
                                time_diff = to_timestamp - from_timestamp
                                time_differences.append(time_diff.total_seconds() / 86400)  # Convert to days
                                break
        
        # Calculate average
        if time_differences:
            avg_days = sum(time_differences) / len(time_differences)
            return {
                'days': round(avg_days, 1),
                'label': f"{round(avg_days, 1)} days",
                'status': 'good'
            }
        
        return {
            'days': 0,
            'label': 'N/A',
            'status': 'good'
        }
    
    def _get_statuses_after(self, status):
        """Get all statuses that come after the given status"""
        status_order = ['new', 'confirmed', 'cad_done', 'user_confirmed', 'rpt_done', 'casting', 'ready', 'delivered']
        
        try:
            index = status_order.index(status)
            return status_order[index + 1:]
        except (ValueError, IndexError):
            return []
    
    def _get_status(self, days, threshold):
        """Determine if stage performance is good, warning, or critical"""
        if days == 0:
            return 'good'
        elif days <= threshold:
            return 'good'
        elif days <= threshold * 1.5:
            return 'warning'
        else:
            return 'critical'


class CombinedOrderAnalyticsAPIView(APIView):
    """
    GET /api/admin/analytics/order-analytics
    
    Returns both order status distribution and stage performance in one call
    
    Query Parameters:
    - start_date: Filter orders created after this date (format: YYYY-MM-DD)
    - end_date: Filter orders created before this date (format: YYYY-MM-DD)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Get status distribution
        status_view = OrderStatusDistributionAPIView()
        status_response = status_view.get(request)
        
        # Check if there was an error in status_view
        if status_response.status_code != 200:
            return status_response
        
        # Get stage performance
        stage_view = StagePerformanceAPIView()
        stage_response = stage_view.get(request)
        
        # Check if there was an error in stage_view
        if stage_response.status_code != 200:
            return stage_response
        
        return Response({
            'order_status_data': status_response.data['status_distribution'],
            'stage_performance': stage_response.data['stage_performance'],
            'total_orders': status_response.data['total_orders'],
            'total_stages': stage_response.data['total_stages'],
            'cad_done': status_response.data['cad_done'],
            'declined': status_response.data['declined'],
            'filters': status_response.data['filters']
        })

# analytics/views.py - TIME TRENDS ANALYTICS API

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate, TruncMonth, ExtractWeekDay
from django.utils import timezone
from datetime import datetime, timedelta
from orders.models import Order


class TimeTrendsAnalyticsAPIView(APIView):
    """
    GET /api/admin/analytics/time-trends
    
    Query Parameters:
    - start_date: YYYY-MM-DD (optional, defaults to 7 days ago for daily, 7 months ago for monthly)
    - end_date: YYYY-MM-DD (optional, defaults to today)
    
    Returns:
    - Daily order volume for the week
    - Monthly growth trend for last 7 months
    - Peak day analysis
    - Same-day orders, approaching deadline, overdue orders
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Get date parameters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # Parse dates or use defaults
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        else:
            end_date = timezone.localtime(timezone.now()).date()
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        else:
            # Default to 7 days ago for daily view
            start_date = end_date - timedelta(days=6)
        
        # Calculate all analytics
        daily_data = self._get_daily_orders(start_date, end_date)
        monthly_data = self._get_monthly_growth(end_date)
        peak_analysis = self._get_peak_analysis(daily_data)
        timeline_alerts = self._get_timeline_alerts()
        
        return Response({
            'daily_orders': daily_data['orders'],
            'daily_summary': {
                'peak_day': peak_analysis['peak_day'],
                'peak_day_orders': peak_analysis['peak_orders'],
                'avg_daily_orders': peak_analysis['avg_orders'],
                'vs_last_week': peak_analysis['vs_last_week']
            },
            'monthly_growth': monthly_data['months'],
            'monthly_summary': {
                'best_month': monthly_data['best_month'],
                'best_month_orders': monthly_data['best_month_orders'],
                'best_month_growth': monthly_data['best_month_growth'],
                'mom_avg_growth': monthly_data['mom_avg_growth'],
                'trend_period': monthly_data['trend_period']
            },
            'timeline_alerts': timeline_alerts,
            'date_range': {
                'start': str(start_date),
                'end': str(end_date)
            }
        })
    
    def _get_daily_orders(self, start_date, end_date):
        """Get daily order volumes for the date range"""
        # Query orders grouped by day
        daily_data = Order.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            orders=Count('id')
        ).order_by('date')
        
        # Create a complete date range (fill missing days with 0)
        date_dict = {item['date']: item['orders'] for item in daily_data}
        
        complete_daily = []
        current_date = start_date
        
        while current_date <= end_date:
            day_name = current_date.strftime('%a')  # Mon, Tue, etc.
            orders = date_dict.get(current_date, 0)
            
            complete_daily.append({
                'day': day_name,
                'date': current_date.strftime('%Y-%m-%d'),
                'orders': orders,
                'revenue': None  # Set to None since you're not using revenue
            })
            current_date += timedelta(days=1)
        
        return {
            'orders': complete_daily,
            'max_orders': max([d['orders'] for d in complete_daily]) if complete_daily else 0
        }
    
    def _get_monthly_growth(self, end_date):
        """Get monthly growth trend for last 7 months"""
        # Calculate start date (7 months ago)
        if end_date.month <= 7:
            start_year = end_date.year - 1
            start_month = end_date.month + 5  # 12 - 7 = 5
        else:
            start_year = end_date.year
            start_month = end_date.month - 6
        
        start_date = end_date.replace(year=start_year, month=start_month, day=1)
        
        # Query orders grouped by month
        monthly_data = Order.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            orders=Count('id')
        ).order_by('month')
        
        # Calculate growth percentages
        months = []
        previous_orders = None
        
        for item in monthly_data:
            month_date = item['month']
            orders = item['orders']
            
            # Calculate growth percentage
            if previous_orders is not None and previous_orders > 0:
                growth = ((orders - previous_orders) / previous_orders) * 100
            else:
                growth = 0
            
            months.append({
                'month': month_date.strftime('%b'),  # Jan, Feb, etc.
                'year': month_date.year,
                'orders': orders,
                'growth': round(growth, 1)
            })
            
            previous_orders = orders
        
        # Find best month
        best_month = max(months, key=lambda x: x['orders']) if months else None
        
        # Calculate average MoM growth
        growth_values = [m['growth'] for m in months if m['growth'] != 0]
        avg_growth = sum(growth_values) / len(growth_values) if growth_values else 0
        
        return {
            'months': months,
            'best_month': best_month['month'] if best_month else '',
            'best_month_orders': best_month['orders'] if best_month else 0,
            'best_month_growth': best_month['growth'] if best_month else 0,
            'mom_avg_growth': round(avg_growth, 1),
            'trend_period': '6 month trend'
        }
    
    def _get_peak_analysis(self, daily_data):
        """Analyze peak day from daily data"""
        orders_list = daily_data['orders']
        
        if not orders_list:
            return {
                'peak_day': 'N/A',
                'peak_orders': 0,
                'avg_orders': 0,
                'vs_last_week': 0
            }
        
        # Find peak day
        peak = max(orders_list, key=lambda x: x['orders'])
        
        # Calculate average
        total_orders = sum(d['orders'] for d in orders_list)
        avg_orders = total_orders // len(orders_list) if orders_list else 0
        
        # Calculate vs last week (simplified - you can enhance this)
        current_week_total = total_orders
        
        # Get last week's data for comparison
        last_week_start = datetime.strptime(orders_list[0]['date'], '%Y-%m-%d').date() - timedelta(days=7)
        last_week_end = datetime.strptime(orders_list[-1]['date'], '%Y-%m-%d').date() - timedelta(days=7)
        
        last_week_total = Order.objects.filter(
            created_at__date__gte=last_week_start,
            created_at__date__lte=last_week_end
        ).count()
        
        if last_week_total > 0:
            vs_last_week = ((current_week_total - last_week_total) / last_week_total) * 100
        else:
            vs_last_week = 0
        
        return {
            'peak_day': peak['day'],
            'peak_orders': peak['orders'],
            'avg_orders': avg_orders,
            'vs_last_week': round(vs_last_week, 1)
        }
    
    def _get_timeline_alerts(self):
        """Get timeline-related alerts"""
        today = timezone.localtime(timezone.now()).date()
        
        # Same-day orders (created and delivered on same day)
        same_day = Order.objects.filter(
            created_at__date=today,
            order_status='delivered',
            updated_at__date=today
        ).count()
        
        # Approaching deadline (within 3 days)
        approaching = Order.objects.filter(
            preferred_delivery_date__lte=today + timedelta(days=3),
            preferred_delivery_date__gte=today,
            order_status__in=['new', 'confirmed', 'cad_done', 'user_confirmed', 'rpt_done', 'casting', 'ready']
        ).count()
        
        # Overdue orders (past preferred delivery date)
        overdue = Order.objects.filter(
            preferred_delivery_date__lt=today,
            order_status__in=['new', 'confirmed', 'cad_done', 'user_confirmed', 'rpt_done', 'casting', 'ready']
        ).count()
        
        return {
            'same_day_orders': same_day,
            'approaching_deadline': approaching,
            'overdue_orders': overdue
        }


class WeeklyOrderVolumeAPIView(APIView):
    """
    GET /api/admin/analytics/weekly-orders
    
    Simplified endpoint for just weekly order volume
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Default to current week
        today = timezone.localtime(timezone.now()).date()
        week_start = today - timedelta(days=today.weekday())  # Monday
        week_end = week_start + timedelta(days=6)  # Sunday
        
        # Query orders for the week
        daily_orders = Order.objects.filter(
            created_at__date__gte=week_start,
            created_at__date__lte=week_end
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            orders=Count('id')
        ).order_by('date')
        
        # Create complete week data
        date_dict = {item['date']: item['orders'] for item in daily_orders}
        
        week_data = []
        day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        
        for i in range(7):
            current_date = week_start + timedelta(days=i)
            orders = date_dict.get(current_date, 0)
            
            week_data.append({
                'day': day_names[i],
                'orders': orders,
                'revenue': None
            })
        
        # Calculate peak and average
        max_orders = max([d['orders'] for d in week_data])
        total_orders = sum([d['orders'] for d in week_data])
        avg_orders = total_orders // 7
        
        peak_day = max(week_data, key=lambda x: x['orders'])
        
        return Response({
            'daily_orders': week_data,
            'max_orders': max_orders,
            'peak_day': peak_day['day'],
            'peak_orders': peak_day['orders'],
            'avg_daily_orders': avg_orders,
            'total_week_orders': total_orders
        })
class MonthlyGrowthAPIView(APIView):
    """
    GET /api/admin/analytics/monthly-growth
    
    Simplified endpoint for just monthly growth trend
    Query Parameters:
    - months: number of months to show (default: 7)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        months_count = int(request.query_params.get('months', 7))
        
        today = timezone.localtime(timezone.now()).date()
        
        # Calculate start date
        if today.month <= months_count:
            start_year = today.year - 1
            start_month = 12 - (months_count - today.month)
        else:
            start_year = today.year
            start_month = today.month - months_count + 1
        
        start_date = today.replace(year=start_year, month=start_month, day=1)
        
        # Query monthly data
        monthly_data = Order.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=today
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            orders=Count('id')
        ).order_by('month')
        
        # Calculate growth
        months = []
        previous_orders = None
        
        for item in monthly_data:
            month_date = item['month']
            orders = item['orders']
            
            if previous_orders is not None and previous_orders > 0:
                growth = ((orders - previous_orders) / previous_orders) * 100
            else:
                growth = 0
            
            months.append({
                'month': month_date.strftime('%b'),
                'year': month_date.year,
                'orders': orders,
                'growth': round(growth, 1)
            })
            
            previous_orders = orders
        
        # Find best month
        best_month = max(months, key=lambda x: x['orders']) if months else None
        
        # Calculate average growth
        growth_values = [m['growth'] for m in months if m['growth'] != 0]
        avg_growth = sum(growth_values) / len(growth_values) if growth_values else 0
        
        return Response({
            'monthly_growth': months,
            'max_orders': max([m['orders'] for m in months]) if months else 0,
            'best_month': {
                'month': best_month['month'] if best_month else '',
                'orders': best_month['orders'] if best_month else 0,
                'growth': best_month['growth'] if best_month else 0
            },
            'mom_avg_growth': round(avg_growth, 1),
            'trend_period': f'{len(months)} month trend'
        })

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone
from datetime import datetime, timedelta
from orders.models import Order


class DailyOrderVolumeAPIView(APIView):
    """
    GET /api/admin/analytics/daily-order-volume
    
    Query Parameters:
    - start_date: YYYY-MM-DD (optional, defaults to 6 days ago)
    - end_date: YYYY-MM-DD (optional, defaults to today)
    
    Returns daily order volume with peak day analysis
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Get date parameters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # Parse dates or use defaults
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        else:
            end_date = timezone.localtime(timezone.now()).date()
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        else:
            # Default to current week (7 days including today)
            start_date = end_date - timedelta(days=6)
        
        # Validate date range
        if start_date > end_date:
            return Response({
                'error': 'start_date cannot be after end_date'
            }, status=400)
        
        # Query orders grouped by day
        daily_data = Order.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            orders=Count('id')
        ).order_by('date')
        
        # Create date dictionary for quick lookup
        date_dict = {item['date']: item['orders'] for item in daily_data}
        
        # Build complete daily data (fill missing days with 0)
        daily_orders = []
        current_date = start_date
        
        while current_date <= end_date:
            day_name = current_date.strftime('%a')  # Mon, Tue, Wed, etc.
            orders = date_dict.get(current_date, 0)
            
            daily_orders.append({
                'day': day_name,
                'date': current_date.strftime('%Y-%m-%d'),
                'orders': orders,
                'revenue': None
            })
            current_date += timedelta(days=1)
        
        # Calculate summary statistics
        total_orders = sum(d['orders'] for d in daily_orders)
        max_orders = max(d['orders'] for d in daily_orders) if daily_orders else 0
        avg_orders = total_orders // len(daily_orders) if daily_orders else 0
        
        # Find peak day
        peak_day_data = max(daily_orders, key=lambda x: x['orders']) if daily_orders else None
        peak_day = peak_day_data['day'] if peak_day_data else 'N/A'
        peak_day_date = peak_day_data['date'] if peak_day_data else 'N/A'
        peak_orders = peak_day_data['orders'] if peak_day_data else 0
        
        # Calculate vs last period (same duration as current period)
        period_length = (end_date - start_date).days + 1
        last_period_start = start_date - timedelta(days=period_length)
        last_period_end = start_date - timedelta(days=1)
        
        last_period_total = Order.objects.filter(
            created_at__date__gte=last_period_start,
            created_at__date__lte=last_period_end
        ).count()
        
        if last_period_total > 0:
            vs_last_period = round(((total_orders - last_period_total) / last_period_total) * 100, 1)
        else:
            vs_last_period = 0.0 if total_orders == 0 else 100.0
        
        return Response({
            'daily_orders': daily_orders,
            'max_orders': max_orders,
            'peak_day': peak_day,
            'peak_day_date': peak_day_date,
            'peak_day_orders': peak_orders,
            'avg_daily_orders': avg_orders,
            'total_orders': total_orders,
            'vs_last_period': vs_last_period,
            'date_range': {
                'start': str(start_date),
                'end': str(end_date),
                'days': period_length
            }
        })

class MonthlyGrowthTrendAPIView(APIView):
    """
    GET /api/admin/analytics/monthly-growth-trend
    
    Query Parameters:
    - start_date: YYYY-MM-DD (optional, calculates from this date)
    - end_date: YYYY-MM-DD (optional, calculates up to this date)
    - months: Number of months to show (optional, default: 7, only used if no dates provided)
    
    Returns monthly order volume with growth percentages
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Get date parameters
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        months_count = int(request.query_params.get('months', 7))
        
        today = timezone.localtime(timezone.now()).date()
        
        # If custom date range is provided, use it
        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            
            # Validate
            if start_date > end_date:
                return Response({
                    'error': 'start_date cannot be after end_date'
                }, status=400)
            
            # Set to first day of start month and last day of end month
            start_date = start_date.replace(day=1)
            
        else:
            # Use months parameter to calculate range
            end_date = today
            
            current_year = today.year
            current_month = today.month
            
            # Go back (months_count - 1) months
            start_month = current_month - (months_count - 1)
            start_year = current_year
            
            # Handle year rollover
            while start_month <= 0:
                start_month += 12
                start_year -= 1
            
            start_date = today.replace(year=start_year, month=start_month, day=1)
        
        # Query monthly data
        monthly_data = Order.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            orders=Count('id')
        ).order_by('month')
        
        # Create dictionary with year-month tuple as key
        month_dict = {}
        for item in monthly_data:
            month_dt = item['month']
            key = (month_dt.year, month_dt.month)
            month_dict[key] = item['orders']
        
        # Build complete monthly data
        monthly_growth = []
        previous_orders = None
        
        # Iterate through all months in range
        current = start_date
        while current <= end_date:
            year = current.year
            month = current.month
            key = (year, month)
            
            # Get orders for this month
            orders = month_dict.get(key, 0)
            
            # Calculate MoM growth
            if previous_orders is not None and previous_orders > 0:
                growth = ((orders - previous_orders) / previous_orders) * 100
            else:
                growth = 0.0
            
            monthly_growth.append({
                'month': current.strftime('%b'),  # Jan, Feb, Mar, etc.
                'year': year,
                'orders': orders,
                'growth': round(growth, 1)
            })
            
            previous_orders = orders
            
            # Move to next month
            if month == 12:
                current = current.replace(year=year + 1, month=1, day=1)
            else:
                current = current.replace(month=month + 1, day=1)
        
        # Find best month
        best_month_data = max(monthly_growth, key=lambda x: x['orders']) if monthly_growth else None
        
        # Calculate max orders
        max_orders = max(m['orders'] for m in monthly_growth) if monthly_growth else 0
        
        # Calculate average MoM growth (excluding zero growth)
        growth_values = [m['growth'] for m in monthly_growth if m['growth'] != 0]
        avg_growth = sum(growth_values) / len(growth_values) if growth_values else 0
        
        return Response({
            'monthly_growth': monthly_growth,
            'max_orders': max_orders,
            'best_month': {
                'name': best_month_data['month'] if best_month_data else '',
                'year': best_month_data['year'] if best_month_data else 0,
                'orders': best_month_data['orders'] if best_month_data else 0,
                'growth': best_month_data['growth'] if best_month_data else 0
            },
            'mom_avg_growth': round(avg_growth, 1),
            'trend_period': f'{len(monthly_growth)} month trend',
            'date_range': {
                'start': str(start_date),
                'end': str(end_date)
            }
        })


class TimelineAlertsAPIView(APIView):
    """
    GET /api/admin/analytics/timeline-alerts
    
    Query Parameters:
    - reference_date: YYYY-MM-DD (optional, defaults to today)
    
    Returns:
    - Same-day orders (created & delivered on reference date)
    - Approaching deadline (orders due within 3 days from reference date)
    - Overdue orders (past preferred delivery date as of reference date)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Get reference date (defaults to today)
        reference_date_str = request.query_params.get('reference_date')
        
        if reference_date_str:
            try:
                reference_date = datetime.strptime(reference_date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({
                    'error': 'Invalid reference_date format. Use YYYY-MM-DD'
                }, status=400)
        else:
            reference_date = timezone.localtime(timezone.now()).date()
        
        # 1. Same-Day Orders
        # Orders created and delivered on the same day (reference date)
        same_day_orders = Order.objects.filter(
            created_at__date=reference_date,
            order_status='delivered',
            updated_at__date=reference_date
        ).count()
        
        # 2. Approaching Deadline
        # Orders due within the next 3 days from reference date (not yet delivered)
        three_days_from_ref = reference_date + timedelta(days=3)
        
        approaching_deadline = Order.objects.filter(
            preferred_delivery_date__gte=reference_date,
            preferred_delivery_date__lte=three_days_from_ref,
            order_status__in=['new', 'confirmed', 'cad_done', 'user_confirmed', 'rpt_done', 'casting', 'ready']
        ).count()
        
        # 3. Overdue Orders
        # Orders past their preferred delivery date as of reference date (not yet delivered)
        overdue_orders = Order.objects.filter(
            preferred_delivery_date__lt=reference_date,
            order_status__in=['new', 'confirmed', 'cad_done', 'user_confirmed', 'rpt_done', 'casting', 'ready']
        ).count()
        
        # Additional useful metrics
        total_active_orders = Order.objects.filter(
            order_status__in=['new', 'confirmed', 'cad_done', 'user_confirmed', 'rpt_done', 'casting', 'ready']
        ).count()
        
        on_time_orders = total_active_orders - overdue_orders - approaching_deadline
        
        return Response({
            'same_day_orders': {
                'count': same_day_orders,
                'label': f'Orders created & delivered on {reference_date.strftime("%Y-%m-%d")}',
                'color': 'blue'
            },
            'approaching_deadline': {
                'count': approaching_deadline,
                'label': f'Orders due within 3 days from {reference_date.strftime("%Y-%m-%d")}',
                'color': 'yellow'
            },
            'overdue_orders': {
                'count': overdue_orders,
                'label': f'Past preferred delivery date as of {reference_date.strftime("%Y-%m-%d")}',
                'color': 'red'
            },
            'summary': {
                'total_active_orders': total_active_orders,
                'on_time_orders': on_time_orders,
                'at_risk_percentage': round((overdue_orders / total_active_orders * 100) if total_active_orders > 0 else 0, 1)
            },
            'reference_date': str(reference_date)
        })


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.db.models import Count, Avg, Q, F, ExpressionWrapper, DurationField
from django.utils import timezone
from datetime import timedelta
from orders.models import Message, Contact, Order

class CommunicationAnalyticsViewV2(APIView):
    """
    GET /api/admin/analytics/communication
    Query params: time_filter, start_date, end_date
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Parse filters
        time_filter = request.query_params.get('time_filter', 'month')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # Calculate date range
        date_range = self._calculate_date_range(time_filter, start_date, end_date)
        start, end = date_range['start'], date_range['end']
        
        # Get all analytics data
        messages_data = self._get_messages_analytics(start, end)
        tickets_data = self._get_tickets_analytics(start, end)
        
        return Response({
            'messages': messages_data,
            'support_tickets': tickets_data,
            'meta': {
                'generated_at': timezone.localtime(timezone.now()).isoformat(),
                'time_filter': time_filter,
                'date_range': {
                    'start': start.isoformat(),
                    'end': end.isoformat()
                }
            }
        })
    
    def _calculate_date_range(self, time_filter, start_date, end_date):
        """Calculate start and end dates based on filter"""
        if start_date and end_date:
            from datetime import datetime
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
        else:
            end = timezone.localtime(timezone.now())
            if time_filter == 'today':
                start = end.replace(hour=0, minute=0, second=0, microsecond=0)
            elif time_filter == 'week':
                start = end - timedelta(days=7)
            elif time_filter == 'month':
                start = end - timedelta(days=30)
            elif time_filter == 'quarter':
                start = end - timedelta(days=90)
            else:  # year
                start = end - timedelta(days=365)
        
        return {'start': start, 'end': end}
    
    def _get_messages_analytics(self, start, end):
        """Get message-related analytics"""
        
        # Filter messages in date range
        messages = Message.objects.filter(created_at__range=[start, end])
        
        # Total messages
        total_messages = messages.count()
        
        # Unread messages
        unread_count = messages.filter(is_read=False).count()
        
        # Messages by sender type
        by_sender = messages.values('sender_type').annotate(count=Count('id'))
        by_sender_dict = {item['sender_type']: item['count'] for item in by_sender}
        
        # Average response time (admin response to user message)
        avg_response_time = self._calculate_avg_response_time(start, end)
        
        # Response rate
        response_rate = self._calculate_response_rate(start, end)
        
        # Messages per order
        total_orders_with_messages = messages.values('order').distinct().count()
        messages_per_order = (total_messages / total_orders_with_messages) if total_orders_with_messages > 0 else 0
        
        # Most discussed orders
        most_discussed = messages.values('order').annotate(
            message_count=Count('id')
        ).order_by('-message_count')[:3]
        
        most_discussed_orders = []
        for item in most_discussed:
            if item['order']:
                order = Order.objects.get(id=item['order'])
                # Determine status based on latest message or order status
                latest_msg = messages.filter(order=order).order_by('-created_at').first()
                status = 'resolved' if order.order_status in ['delivered', 'declined'] else 'active'
                
                most_discussed_orders.append({
                    'order_id': order.id,
                    'order_number': order.order_id,
                    'message_count': item['message_count'],
                    'status': status
                })
        
        return {
            'total_messages': total_messages,
            'unread_count': unread_count,
            'avg_response_time_hours': avg_response_time,
            'response_rate': response_rate,
            'by_sender_type': {
                'user': by_sender_dict.get('user', 0),
                'admin': by_sender_dict.get('admin', 0),
                'system': by_sender_dict.get('system', 0)
            },
            'messages_per_order': round(messages_per_order, 1),
            'most_discussed_orders': most_discussed_orders
        }
    
    def _calculate_avg_response_time(self, start, end):
        """
        Calculate average time between user message and admin response
        """
        from django.db.models import Avg, F, ExpressionWrapper, DurationField
        
        # Get all user messages in the period
        user_messages = Message.objects.filter(
            sender_type='user',
            created_at__range=[start, end]
        ).order_by('order', 'created_at')
        
        response_times = []
        
        for user_msg in user_messages:
            # Find the next admin message for the same order
            admin_response = Message.objects.filter(
                order=user_msg.order,
                sender_type='admin',
                created_at__gt=user_msg.created_at
            ).order_by('created_at').first()
            
            if admin_response:
                time_diff = admin_response.created_at - user_msg.created_at
                response_times.append(time_diff.total_seconds() / 3600)  # Convert to hours
        
        if response_times:
            avg_hours = sum(response_times) / len(response_times)
            return round(avg_hours, 1)
        
        return 0
    
    def _calculate_response_rate(self, start, end):
        """
        Calculate percentage of user messages that received admin replies
        """
        user_messages = Message.objects.filter(
            sender_type='user',
            created_at__range=[start, end]
        )
        
        total_user_messages = user_messages.count()
        if total_user_messages == 0:
            return 0
        
        # Count how many have admin responses
        messages_with_response = 0
        for user_msg in user_messages:
            has_response = Message.objects.filter(
                order=user_msg.order,
                sender_type='admin',
                created_at__gt=user_msg.created_at
            ).exists()
            
            if has_response:
                messages_with_response += 1
        
        response_rate = (messages_with_response / total_user_messages) * 100
        return round(response_rate, 1)
    
    def _get_tickets_analytics(self, start, end):
        """Get support ticket analytics"""
        
        # Filter tickets in date range
        tickets = Contact.objects.filter(created_at__range=[start, end])
        
        total_tickets = tickets.count()
        
        # Tickets by status
        by_status = tickets.values('status').annotate(count=Count('id'))
        status_dict = {item['status']: item['count'] for item in by_status}
        
        # Calculate percentages
        status_distribution = []
        for status in ['resolved', 'in_progress', 'new', 'closed']:
            count = status_dict.get(status, 0)
            percentage = (count / total_tickets * 100) if total_tickets > 0 else 0
            status_distribution.append({
                'status': status,
                'count': count,
                'percentage': round(percentage, 1)
            })
        
        # Open tickets (new + in_progress)
        open_tickets = tickets.filter(status__in=['new', 'in_progress']).count()
        
        # Resolution rate
        resolved_closed = tickets.filter(status__in=['resolved', 'closed']).count()
        resolution_rate = (resolved_closed / total_tickets * 100) if total_tickets > 0 else 0
        
        # Average resolution time
        avg_resolution_time = self._calculate_avg_resolution_time(start, end)
        
        # By contact method
        by_method = tickets.values('preferred_contact_method').annotate(count=Count('id'))
        method_dict = {item['preferred_contact_method']: item['count'] for item in by_method}
        
        contact_methods = []
        for method in ['email', 'phone', 'either']:
            count = method_dict.get(method, 0)
            percentage = (count / total_tickets * 100) if total_tickets > 0 else 0
            contact_methods.append({
                'method': method,
                'count': count,
                'percentage': round(percentage, 1)
            })
        
        # Order related vs general
        order_related = tickets.filter(order_related=True).count()
        general = tickets.filter(order_related=False).count()
        
        # Unanswered tickets (assuming you have a response tracking)
        # If you don't have this, you can use admin_response field
        unanswered_tickets = tickets.filter(
            Q(admin_response__isnull=True) | Q(admin_response='')
        ).count()
        
        # Most active days
        from django.db.models.functions import TruncDate
        by_date = tickets.annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('-count')[:7]
        
        most_active_days = [
            {
                'day': item['date'].strftime('%A'),
                'count': item['count']
            }
            for item in by_date
        ]
        
        return {
            'total_tickets': total_tickets,
            'by_status': status_distribution,
            'open_tickets': open_tickets,
            'resolution_rate': round(resolution_rate, 1),
            'avg_resolution_time_hours': avg_resolution_time,
            'by_contact_method': contact_methods,
            'order_related_vs_general': {
                'order_related': order_related,
                'general': general
            },
            'unanswered_tickets': unanswered_tickets,
            'most_active_days': most_active_days
        }
    
    def _calculate_avg_resolution_time(self, start, end):
        """
        Calculate average time from ticket creation to resolved/closed status
        """
        resolved_tickets = Contact.objects.filter(
            created_at__range=[start, end],
            status__in=['resolved', 'closed'],
            updated_at__isnull=False
        )
        
        resolution_times = []
        for ticket in resolved_tickets:
            time_diff = ticket.updated_at - ticket.created_at
            resolution_times.append(time_diff.total_seconds() / 3600)  # Convert to hours
        
        if resolution_times:
            avg_hours = sum(resolution_times) / len(resolution_times)
            return round(avg_hours, 1)
        
        return 0



from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Avg, Q, F, Min, Max
from django.utils import timezone
from datetime import timedelta, datetime
from orders.models import Order


class CustomerAnalyticsView(APIView):
    """
    GET /api/admin/analytics/customers
    Query params: time_filter, start_date, end_date
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Parse filters
        time_filter = request.query_params.get('time_filter', 'month')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # Calculate date range
        date_range = self._calculate_date_range(time_filter, start_date, end_date)
        start, end = date_range['start'], date_range['end']
        
        # Calculate previous period for comparison
        period_length = (end - start).days
        prev_start = start - timedelta(days=period_length)
        prev_end = start
        
        # Get all analytics data
        user_base_data = self._get_user_base_metrics(start, end, prev_start, prev_end)
        engagement_data = self._get_engagement_metrics(start, end)
        top_customers_data = self._get_top_customers(start, end, limit=10)
        behavior_data = self._get_behavior_metrics(start, end)
        
        return Response({
            'user_base': user_base_data,
            'engagement': engagement_data,
            'top_customers': top_customers_data,
            'behavior': behavior_data,
            'meta': {
                'generated_at': timezone.localtime(timezone.now()).isoformat(),
                'time_filter': time_filter,
                'date_range': {
                    'start': start.isoformat(),
                    'end': end.isoformat()
                }
            }
        })
    
    def _calculate_date_range(self, time_filter, start_date, end_date):
        """Calculate start and end dates based on filter"""
        if start_date and end_date:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            # Make end date inclusive of the entire day
            end = datetime.combine(end.date(), datetime.max.time())
            # Make start and end timezone-aware
            start = timezone.make_aware(start) if timezone.is_naive(start) else start
            end = timezone.make_aware(end) if timezone.is_naive(end) else end
        else:
            end = timezone.localtime(timezone.now())
            if time_filter == 'today':
                start = end.replace(hour=0, minute=0, second=0, microsecond=0)
            elif time_filter == 'week':
                start = end - timedelta(days=7)
            elif time_filter == 'month':
                start = end - timedelta(days=30)
            elif time_filter == 'quarter':
                start = end - timedelta(days=90)
            else:  # year
                start = end - timedelta(days=365)
        
        return {'start': start, 'end': end}
    
    def _get_user_base_metrics(self, start, end, prev_start, prev_end):
        """Get user base metrics with growth calculations"""
        
        # Total customers (all customers up to end date)
        total_customers = User.objects.filter(
            user_type='customer',
            date_joined__lte=end
        ).count()
        
        prev_total_customers = User.objects.filter(
            user_type='customer',
            date_joined__lt=start
        ).count()
        total_change = self._calculate_percentage_change(total_customers, prev_total_customers)
        
        # Active customers (placed at least one order in period)
        active_customers = User.objects.filter(
            user_type='customer',
            orders__created_at__range=[start, end]
        ).distinct().count()
        
        prev_active_customers = User.objects.filter(
            user_type='customer',
            orders__created_at__range=[prev_start, prev_end]
        ).distinct().count()
        active_change = self._calculate_percentage_change(active_customers, prev_active_customers)
        
        # New registrations in current period
        new_registrations = User.objects.filter(
            user_type='customer',
            date_joined__range=[start, end]
        ).count()
        
        prev_new_registrations = User.objects.filter(
            user_type='customer',
            date_joined__range=[prev_start, prev_end]
        ).count()
        new_reg_change = self._calculate_percentage_change(new_registrations, prev_new_registrations)
        
        # Repeat customers (customers with 2+ orders in period)
        repeat_customers = User.objects.filter(
            user_type='customer',
            orders__created_at__range=[start, end]
        ).annotate(
            order_count=Count('orders', filter=Q(orders__created_at__range=[start, end]))
        ).filter(order_count__gte=2).count()
        
        prev_repeat_customers = User.objects.filter(
            user_type='customer',
            orders__created_at__range=[prev_start, prev_end]
        ).annotate(
            order_count=Count('orders', filter=Q(orders__created_at__range=[prev_start, prev_end]))
        ).filter(order_count__gte=2).count()
        repeat_change = self._calculate_percentage_change(repeat_customers, prev_repeat_customers)
        
        # Total admins (all time)
        total_admins = User.objects.filter(user_type='admin').count()
        
        # New registrations breakdown
        now = timezone.localtime(timezone.now())
        new_reg_today = User.objects.filter(
            user_type='customer',
            date_joined__date=now.date()
        ).count()
        
        new_reg_week = User.objects.filter(
            user_type='customer',
            date_joined__gte=now - timedelta(days=7)
        ).count()
        
        new_reg_month = User.objects.filter(
            user_type='customer',
            date_joined__gte=now - timedelta(days=30)
        ).count()
        
        # Growth rate (registrations as percentage of previous total)
        growth_rate = (new_registrations / prev_total_customers * 100) if prev_total_customers > 0 else 0
        
        return {
            'total_customers': {
                'value': total_customers,
                'change_percentage': round(total_change, 1),
                'change_label': 'vs last period'
            },
            'active_customers': {
                'value': active_customers,
                'change_percentage': round(active_change, 1),
                'change_label': 'vs last period'
            },
            'new_registrations': {
                'value': new_registrations,
                'change_percentage': round(new_reg_change, 1),
                'change_label': 'vs last period',
                'breakdown': {
                    'today': new_reg_today,
                    'week': new_reg_week,
                    'month': new_reg_month
                }
            },
            'repeat_customers': {
                'value': repeat_customers,
                'change_percentage': round(repeat_change, 1),
                'change_label': 'vs last period'
            },
            'total_admins': total_admins,
            'growth_rate': round(growth_rate, 1)
        }
    
    def _get_engagement_metrics(self, start, end):
        """Get customer engagement metrics FOR THE FILTERED PERIOD"""
        
        # All customers who were registered before or during the period
        all_customers = User.objects.filter(
            user_type='customer',
            date_joined__lte=end
        )
        total_customers = all_customers.count()
        
        # Active customers (placed at least one order IN THIS PERIOD)
        active_customers = all_customers.filter(
            orders__created_at__range=[start, end]
        ).distinct()
        active_count = active_customers.count()
        
        # Inactive customers (no orders IN THIS PERIOD)
        inactive_count = total_customers - active_count
        
        # Repeat customers (2+ orders IN THIS PERIOD)
        repeat_customers = all_customers.annotate(
            order_count=Count('orders', filter=Q(orders__created_at__range=[start, end]))
        ).filter(order_count__gte=2)
        repeat_count = repeat_customers.count()
        
        # Average orders per customer (only for active customers IN THIS PERIOD)
        total_orders = Order.objects.filter(
            customer__user_type='customer',
            created_at__range=[start, end]
        ).count()
        avg_orders_per_customer = (total_orders / active_count) if active_count > 0 else 0
        
        # Customer retention rate (percentage who made 2+ orders IN THIS PERIOD)
        retention_rate = (repeat_count / active_count * 100) if active_count > 0 else 0
        
        # Average days between orders for repeat customers IN THIS PERIOD
        avg_days_between = self._calculate_avg_days_between_orders(start, end)
        
        return {
            'active_customers': active_count,
            'inactive_customers': inactive_count,
            'repeat_customers': repeat_count,
            'avg_orders_per_customer': round(avg_orders_per_customer, 2),
            'customer_retention_rate': round(retention_rate, 1),
            'avg_days_between_orders': avg_days_between
        }
    
    def _calculate_avg_days_between_orders(self, start, end):
        """Calculate average days between consecutive orders for repeat customers IN THE FILTERED PERIOD"""
        
        # Get customers with 2+ orders IN THIS PERIOD
        repeat_customers = User.objects.filter(
            user_type='customer'
        ).annotate(
            order_count=Count('orders', filter=Q(orders__created_at__range=[start, end]))
        ).filter(order_count__gte=2)
        
        total_days = 0
        total_gaps = 0
        
        for customer in repeat_customers:
            # Get orders IN THIS PERIOD only
            orders = customer.orders.filter(
                created_at__range=[start, end]
            ).order_by('created_at')
            
            if orders.count() < 2:
                continue
            
            # Calculate gaps between consecutive orders
            orders_list = list(orders)
            for i in range(1, len(orders_list)):
                gap = (orders_list[i].created_at - orders_list[i-1].created_at).days
                total_days += gap
                total_gaps += 1
        
        return round(total_days / total_gaps) if total_gaps > 0 else 0
    
    def _get_top_customers(self, start, end, limit=10):
        """Get top customers by order count IN THE FILTERED PERIOD"""
        
        # Get customers with their order counts IN THIS PERIOD
        customers = User.objects.filter(
            user_type='customer',
            orders__created_at__range=[start, end]
        ).annotate(
            order_count=Count('orders', filter=Q(orders__created_at__range=[start, end])),
            last_order_date=Max('orders__created_at', filter=Q(orders__created_at__range=[start, end]))
        ).filter(order_count__gt=0).order_by('-order_count')[:limit]
        
        top_customers = []
        for customer in customers:
            # Determine status based on order count IN THIS PERIOD
            if customer.order_count >= 10:
                status = 'VIP'
            elif customer.order_count >= 7:
                status = 'Gold'
            elif customer.order_count >= 4:
                status = 'Silver'
            else:
                status = 'Regular'
            
            top_customers.append({
                'id': customer.id,
                'name': f"{customer.first_name} {customer.last_name}".strip() or customer.email.split('@')[0],
                'email': customer.email,
                'orders_count': customer.order_count,
                'status': status,
                'last_order_date': customer.last_order_date.isoformat() if customer.last_order_date else None
            })
        
        return top_customers
    
    def _get_behavior_metrics(self, start, end):
        """Get customer behavior metrics IN THE FILTERED PERIOD"""
        
        # Orders in period
        orders = Order.objects.filter(created_at__range=[start, end])
        
        # First-time customers (users who placed their first order in this period)
        first_time = 0
        returning = 0
        
        for order in orders:
            # Check if this is the user's first order EVER (not just in this period)
            first_order = order.customer.orders.order_by('created_at').first()
            if first_order and first_order.id == order.id:
                first_time += 1
            else:
                returning += 1
        
        return {
            'first_time_customers': first_time,
            'returning_customers': returning
        }
    
    def _calculate_percentage_change(self, current, previous):
        """Calculate percentage change between two values"""
        if previous == 0:
            return 100 if current > 0 else 0
        return ((current - previous) / previous) * 100


# analytics/views.py - KPI CARDS API (with start_date/end_date params)

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.db.models import Count, Avg, ExpressionWrapper, DurationField, F
from django.utils import timezone
from datetime import datetime, timedelta
from orders.models import Order, Contact
from users.models import CustomUser


def parse_date(param, default_date):
    """Parse YYYY-MM-DD string, strip quotes; return date or default"""
    if not param:
        return default_date
    p = param.strip("'\"")
    try:
        return datetime.strptime(p, '%Y-%m-%d').date()
    except ValueError:
        return default_date


class KPICardsAPIView(APIView):
    """
    GET /api/admin/analytics/kpi-cards

    Query Parameters:
    - start_date: YYYY-MM-DD (inclusive)
    - end_date: YYYY-MM-DD (inclusive)

    Returns key performance indicator cards with comparisons
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Default to last 30 days
        ist_today = timezone.localtime(timezone.now()).date()
        default_start = ist_today - timedelta(days=29)
        default_end = ist_today

        # Parse query params
        start_date = parse_date(request.query_params.get('start_date'), default_start)
        end_date = parse_date(request.query_params.get('end_date'), default_end)

        # Compute previous period of same length
        delta = end_date - start_date
        prev_end = start_date - timedelta(days=1)
        prev_start = prev_end - delta

        # KPIs
        total_orders = self._total_orders(start_date, end_date, prev_start, prev_end)
        active_customers = self._active_customers(start_date, end_date, prev_start, prev_end)
        avg_completion = self._avg_completion_time(start_date, end_date, prev_start, prev_end)
        support_resolution = self._support_resolution(start_date, end_date, prev_start, prev_end)
        completion_rate = self._completion_rate(start_date, end_date, prev_start, prev_end)
        pending_approvals = self._pending_approvals(start_date, end_date, prev_start, prev_end)

        return Response({
            'total_orders': total_orders,
            'active_customers': active_customers,
            'avg_completion_time': avg_completion,
            'support_resolution': support_resolution,
            'completion_rate': completion_rate,
            'pending_approvals': pending_approvals,
            'date_range': {
                'start_date': str(start_date),
                'end_date': str(end_date),
                'previous_start': str(prev_start),
                'previous_end': str(prev_end)
            }
        })

    def _pct(self, cur, prev):
        if prev == 0:
            return 100.0 if cur > 0 else 0.0
        return round(((cur - prev) / prev) * 100, 1)

    def _label(self, pct, suffix='vs previous period'):
        sign = '+' if pct > 0 else ''
        return f"{sign}{pct}% {suffix}"

    def _total_orders(self, s, e, ps, pe):
        cur = Order.objects.filter(created_at__date__gte=s, created_at__date__lte=e).count()
        prev = Order.objects.filter(created_at__date__gte=ps, created_at__date__lte=pe).count()
        pct = self._pct(cur, prev)
        return {'value': cur, 'change_percentage': pct, 'change_label': self._label(pct), 'icon': 'Package', 'color': 'orange'}

    def _active_customers(self, s, e, ps, pe):
        cur = CustomUser.objects.filter(user_type='customer', orders__created_at__date__gte=s, orders__created_at__date__lte=e).distinct().count()
        prev = CustomUser.objects.filter(user_type='customer', orders__created_at__date__gte=ps, orders__created_at__date__lte=pe).distinct().count()
        pct = self._pct(cur, prev)
        return {'value': cur, 'change_percentage': pct, 'change_label': self._label(pct), 'icon': 'Users', 'color': 'purple'}

    def _avg_completion_time(self, s, e, ps, pe):
        cur_qs = Order.objects.filter(order_status='delivered', updated_at__date__gte=s, updated_at__date__lte=e)
        cur_avg = cur_qs.annotate(diff=ExpressionWrapper(F('updated_at')-F('created_at'), output_field=DurationField())).aggregate(avg=Avg('diff'))['avg']
        cur_days = cur_avg.days if cur_avg else 0
        prev_qs = Order.objects.filter(order_status='delivered', updated_at__date__gte=ps, updated_at__date__lte=pe)
        prev_avg = prev_qs.annotate(diff=ExpressionWrapper(F('updated_at')-F('created_at'), output_field=DurationField())).aggregate(avg=Avg('diff'))['avg']
        prev_days = prev_avg.days if prev_avg else 0
        pct = self._pct(cur_days, prev_days)
        return {'value': f"{cur_days} days", 'change_percentage': pct, 'change_label': self._label(pct), 'icon': 'Clock', 'color': 'green'}

    def _support_resolution(self, s, e, ps, pe):
        cur_tot = Contact.objects.filter(created_at__date__gte=s, created_at__date__lte=e).count()
        cur_res = Contact.objects.filter(created_at__date__gte=s, created_at__date__lte=e, status__in=['resolved','closed']).count()
        cur_pct = round((cur_res/cur_tot*100) if cur_tot else 0,1)
        prev_tot = Contact.objects.filter(created_at__date__gte=ps, created_at__date__lte=pe).count()
        prev_res = Contact.objects.filter(created_at__date__gte=ps, created_at__date__lte=pe, status__in=['resolved','closed']).count()
        prev_pct = round((prev_res/prev_tot*100) if prev_tot else 0,1)
        pct = round(cur_pct - prev_pct,1)
        return {'value': f"{cur_pct}%", 'change_percentage': pct, 'change_label': self._label(pct,'vs last period'), 'icon': 'MessageCircle', 'color': 'blue'}

    def _completion_rate(self, s, e, ps, pe):
        cur_tot = Order.objects.filter(created_at__date__gte=s, created_at__date__lte=e).exclude(order_status='declined').count()
        cur_com = Order.objects.filter(created_at__date__gte=s, created_at__date__lte=e, order_status='delivered').count()
        cur_pct = round((cur_com/cur_tot*100) if cur_tot else 0,1)
        prev_tot = Order.objects.filter(created_at__date__gte=ps, created_at__date__lte=pe).exclude(order_status='declined').count()
        prev_com = Order.objects.filter(created_at__date__gte=ps, created_at__date__lte=pe, order_status='delivered').count()
        prev_pct = round((prev_com/prev_tot*100) if prev_tot else 0,1)
        pct = round(cur_pct - prev_pct,1)
        return {'value': f"{cur_pct}%", 'change_percentage': pct, 'change_label': self._label(pct), 'icon': 'TrendingUp', 'color': 'green'}

    def _pending_approvals(self, s, e, ps, pe):
        cur = Order.objects.filter(order_status='cad_done').count()
        prev = Order.objects.filter(order_status='cad_done', created_at__date__lte=pe).count()
        pct = self._pct(cur, prev)
        return {'value': cur, 'change_percentage': pct, 'change_label': self._label(pct), 'icon': 'Package', 'color': 'yellow'}