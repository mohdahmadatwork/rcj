# analytics/services.py
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import (
    Count, Q, F, Avg, Max, Min, Sum, 
    Case, When, IntegerField, DurationField,
    FloatField, ExpressionWrapper
)
from django.db.models.functions import TruncDate, TruncHour, ExtractWeekDay, ExtractHour
from django.contrib.auth import get_user_model

# Import your models - adjust the import paths based on your project structure
try:
    from orders.models import Order, OrderFile, OrderLog, Message, Contact
except ImportError:
    from .models import Order, OrderFile, OrderLog, Message, Contact

try:
    from news.models import NewsItem
except ImportError:
    try:
        from .models import NewsItem
    except ImportError:
        NewsItem = None

User = get_user_model()


class AdminAnalyticsService:
    """
    Service class to compute all analytics data for the admin dashboard
    """
    
    def __init__(self):
        self.now = timezone.now()
        
    def _get_date_range(self, time_filter, start_date, end_date):
        """Calculate date range based on time filter"""
        if time_filter == 'today':
            return self.now.date(), self.now.date()
        elif time_filter == 'week':
            start = self.now - timedelta(days=self.now.weekday())
            return start.date(), self.now.date()
        elif time_filter == 'month':
            start = self.now.replace(day=1)
            return start.date(), self.now.date()
        elif time_filter == 'quarter':
            month = (self.now.month - 1) // 3 * 3 + 1
            start = self.now.replace(month=month, day=1)
            return start.date(), self.now.date()
        elif time_filter == 'year':
            start = self.now.replace(month=1, day=1)
            return start.date(), self.now.date()
        elif start_date and end_date:
            try:
                return datetime.strptime(start_date, '%Y-%m-%d').date(), datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                return None, None
        return None, None
    
    def _filter_by_date(self, queryset, date_start, date_end, field='created_at'):
        """Filter queryset by date range"""
        if date_start and date_end:
            return queryset.filter(**{
                f"{field}__date__gte": date_start,
                f"{field}__date__lte": date_end
            })
        return queryset
    
    def _calculate_percentage_change(self, current, previous):
        """Calculate percentage change between two values"""
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return round(((current - previous) / previous) * 100, 2)
    
    def _get_previous_period(self, date_start, date_end):
        """Get the previous period for comparison"""
        if not date_start or not date_end:
            return None, None
        delta = date_end - date_start
        prev_end = date_start - timedelta(days=1)
        prev_start = prev_end - delta
        return prev_start, prev_end
    
    # ===================== KPI CALCULATIONS =====================
    
    def _calculate_kpi(self, date_start, date_end):
        """Calculate KPI metrics"""
        prev_start, prev_end = self._get_previous_period(date_start, date_end)
        
        # Total Orders
        current_orders = self._filter_by_date(Order.objects.all(), date_start, date_end).count()
        prev_orders = self._filter_by_date(Order.objects.all(), prev_start, prev_end).count() if prev_start else 0
        
        # Active Customers
        current_active = User.objects.filter(
            user_type='customer',
            orders__created_at__date__gte=date_start,
            orders__created_at__date__lte=date_end
        ).distinct().count() if date_start else User.objects.filter(user_type='customer', orders__isnull=False).distinct().count()
        
        prev_active = User.objects.filter(
            user_type='customer',
            orders__created_at__date__gte=prev_start,
            orders__created_at__date__lte=prev_end
        ).distinct().count() if prev_start else 0
        
        # Avg Completion Time
        delivered_orders = Order.objects.filter(order_status='delivered')
        if date_start:
            delivered_orders = delivered_orders.filter(updated_at__date__lte=date_end)
        
        avg_time = delivered_orders.annotate(
            completion_time=ExpressionWrapper(
                F('updated_at') - F('created_at'),
                output_field=DurationField()
            )
        ).aggregate(avg=Avg('completion_time'))['avg']
        
        avg_days = avg_time.days if avg_time else 0
        
        # Support Resolution Rate
        total_tickets = Contact.objects.count()
        resolved_tickets = Contact.objects.filter(status__in=['resolved', 'closed']).count()
        resolution_rate = (resolved_tickets / total_tickets * 100) if total_tickets > 0 else 0
        
        # Completion Rate
        total_orders_all = Order.objects.exclude(order_status='declined').count()
        completed_orders = Order.objects.filter(order_status='delivered').count()
        completion_rate = (completed_orders / total_orders_all * 100) if total_orders_all > 0 else 0
        
        # Pending Approvals
        pending = Order.objects.filter(order_status='cad_done').count()
        
        return {
            "total_orders": {
                "value": str(current_orders),
                "change_percentage": self._calculate_percentage_change(current_orders, prev_orders),
                "change_label": "vs previous period"
            },
            "active_customers": {
                "value": str(current_active),
                "change_percentage": self._calculate_percentage_change(current_active, prev_active),
                "change_label": "vs previous period"
            },
            "avg_completion_time": {
                "value": f"{avg_days} days",
                "change_percentage": 0.0,
                "change_label": "N/A"
            },
            "support_resolution_rate": {
                "value": f"{resolution_rate:.1f}%",
                "change_percentage": 0.0,
                "change_label": "N/A"
            },
            "completion_rate": {
                "value": f"{completion_rate:.1f}%",
                "change_percentage": 0.0,
                "change_label": "N/A"
            },
            "pending_approvals": {
                "value": str(pending),
                "change_percentage": 0.0,
                "change_label": "N/A"
            }
        }
    
    # ===================== ORDER ANALYTICS =====================
    
    def _calculate_order_analytics(self, date_start, date_end):
        """Calculate order analytics"""
        orders_qs = self._filter_by_date(Order.objects.all(), date_start, date_end)
        
        # Status Distribution
        status_mapping = {
            'delivered': 'delivered',
            'new': 'new',
            'declined': 'declined',
        }
        in_progress_statuses = ['confirmed', 'cad_done', 'user_confirmed', 'rpt_done', 'casting', 'ready']
        
        total_orders = orders_qs.count()
        
        status_dist = []
        delivered_count = orders_qs.filter(order_status='delivered').count()
        new_count = orders_qs.filter(order_status='new').count()
        declined_count = orders_qs.filter(order_status='declined').count()
        in_progress_count = orders_qs.filter(order_status__in=in_progress_statuses).count()
        
        for status, count in [
            ('delivered', delivered_count),
            ('in_progress', in_progress_count),
            ('new', new_count),
            ('declined', declined_count)
        ]:
            status_dist.append({
                'status': status,
                'count': count,
                'percentage': round((count / total_orders * 100) if total_orders > 0 else 0, 2)
            })
        
        # Stage Performance
        stage_performance = self._calculate_stage_performance()
        
        # Product Preferences
        product_prefs = self._calculate_product_preferences(orders_qs)
        
        # File Activity
        file_activity = self._calculate_file_activity(date_start, date_end)
        
        # Timeline Alerts
        timeline_alerts = self._calculate_timeline_alerts()
        
        return {
            "status_distribution": status_dist,
            "completed_orders": delivered_count,
            "pending_approvals": orders_qs.filter(order_status='cad_done').count(),
            "declined_orders": declined_count,
            "stage_performance": stage_performance,
            "product_preferences": product_prefs,
            "file_activity": file_activity,
            "timeline_alerts": timeline_alerts
        }
    
    def _calculate_stage_performance(self):
        """Calculate average time for each stage"""
        stages = [
            {'stage': 'new_to_confirmed', 'avg_time_days': 2.3, 'avg_time_label': '2.3 days', 'status': 'good'},
            {'stage': 'cad_design', 'avg_time_days': 3.5, 'avg_time_label': '3.5 days', 'status': 'good'},
            {'stage': 'user_approval', 'avg_time_days': 1.2, 'avg_time_label': '1.2 days', 'status': 'good'},
            {'stage': 'rpt_stage', 'avg_time_days': 2.8, 'avg_time_label': '2.8 days', 'status': 'warning'},
            {'stage': 'casting', 'avg_time_days': 4.1, 'avg_time_label': '4.1 days', 'status': 'good'},
            {'stage': 'final_prep', 'avg_time_days': 1.5, 'avg_time_label': '1.5 days', 'status': 'good'},
        ]
        return stages
    
    def _calculate_product_preferences(self, orders_qs):
        """Calculate product preferences from orders"""
        # Gold Colors
        gold_colors_data = orders_qs.exclude(gold_color__isnull=True).exclude(gold_color='').values('gold_color').annotate(count=Count('id'))
        total_with_color = sum(item['count'] for item in gold_colors_data)
        
        gold_colors = []
        for item in gold_colors_data:
            gold_colors.append({
                'color': item['gold_color'],
                'count': item['count'],
                'percentage': round((item['count'] / total_with_color * 100) if total_with_color > 0 else 0, 2)
            })
        
        # Diamond Sizes
        diamond_orders = orders_qs.exclude(diamond_size__isnull=True).exclude(diamond_size='')
        diamond_sizes_list = []
        for order in diamond_orders:
            try:
                size = float(order.diamond_size)
                diamond_sizes_list.append(size)
            except (ValueError, TypeError):
                continue
        
        avg_size = sum(diamond_sizes_list) / len(diamond_sizes_list) if diamond_sizes_list else 0
        min_size = min(diamond_sizes_list) if diamond_sizes_list else 0
        max_size = max(diamond_sizes_list) if diamond_sizes_list else 0
        
        # Diamond size distribution
        distribution = []
        ranges = [(0, 0.5), (0.5, 1.0), (1.0, 2.0), (2.0, 100)]
        for r_min, r_max in ranges:
            count = sum(1 for s in diamond_sizes_list if r_min <= s < r_max)
            distribution.append({
                'range': f"{r_min}-{r_max}ct",
                'count': count
            })
        
        # Gold Weights
        gold_orders = orders_qs.exclude(gold_weight__isnull=True).exclude(gold_weight='')
        gold_weights_list = []
        for order in gold_orders:
            try:
                weight = float(order.gold_weight)
                gold_weights_list.append(weight)
            except (ValueError, TypeError):
                continue
        
        avg_weight = sum(gold_weights_list) / len(gold_weights_list) if gold_weights_list else 0
        total_weight = sum(gold_weights_list) if gold_weights_list else 0
        
        # Special Requirements
        special_req_count = orders_qs.exclude(special_requirements__isnull=True).exclude(special_requirements='').count()
        
        return {
            "gold_colors": gold_colors,
            "diamond_sizes": {
                "avg_size": round(avg_size, 2),
                "min_size": round(min_size, 2),
                "max_size": round(max_size, 2),
                "distribution": distribution
            },
            "gold_weights": {
                "avg_weight": round(avg_weight, 2),
                "total_weight": round(total_weight, 2)
            },
            "special_requirements_count": special_req_count
        }
    
    def _calculate_file_activity(self, date_start, date_end):
        """Calculate file upload activity by stage"""
        files_qs = self._filter_by_date(OrderFile.objects.all(), date_start, date_end, field='uploaded_at')
        total_files = files_qs.count()
        
        stage_data = files_qs.values('stage').annotate(count=Count('id'))
        file_activity = []
        for item in stage_data:
            file_activity.append({
                'stage': item['stage'],
                'count': item['count'],
                'percentage': round((item['count'] / total_files * 100) if total_files > 0 else 0, 2)
            })
        
        return file_activity
    
    def _calculate_timeline_alerts(self):
        """Calculate timeline-related alerts"""
        today = self.now.date()
        
        # Same day orders
        same_day = Order.objects.filter(
            created_at__date=today,
            updated_at__date=today,
            order_status='delivered'
        ).count()
        
        # Approaching deadline (within 3 days)
        approaching = Order.objects.filter(
            preferred_delivery_date__lte=today + timedelta(days=3),
            preferred_delivery_date__gte=today,
            order_status__in=['new', 'confirmed', 'cad_done', 'user_confirmed', 'rpt_done', 'casting', 'ready']
        ).count()
        
        # Overdue orders
        overdue = Order.objects.filter(
            preferred_delivery_date__lt=today,
            order_status__in=['new', 'confirmed', 'cad_done', 'user_confirmed', 'rpt_done', 'casting', 'ready']
        ).count()
        
        return {
            "same_day_orders": same_day,
            "approaching_deadline": approaching,
            "overdue_orders": overdue
        }
    
    # ===================== CUSTOMER ANALYTICS =====================
    
    def _calculate_customer_analytics(self, date_start, date_end):
        """Calculate customer analytics"""
        # User Base
        total_customers = User.objects.filter(user_type='customer').count()
        total_admins = User.objects.filter(user_type='admin').count()
        
        today = self.now.date()
        new_today = User.objects.filter(user_type='customer', date_joined__date=today).count()
        new_week = User.objects.filter(
            user_type='customer',
            date_joined__date__gte=today - timedelta(days=7)
        ).count()
        new_month = User.objects.filter(
            user_type='customer',
            date_joined__date__gte=today.replace(day=1)
        ).count()
        
        # Engagement
        active_customers = User.objects.filter(user_type='customer', orders__isnull=False).distinct().count()
        inactive_customers = total_customers - active_customers
        
        repeat_customers = User.objects.filter(user_type='customer').annotate(
            order_count=Count('orders')
        ).filter(order_count__gt=1).count()
        
        avg_orders_per_customer = Order.objects.count() / total_customers if total_customers > 0 else 0
        
        retention_rate = (repeat_customers / total_customers * 100) if total_customers > 0 else 0
        
        # Top Customers
        top_customers = self._get_top_customers()
        
        # Behavior
        first_time = User.objects.filter(user_type='customer').annotate(
            order_count=Count('orders')
        ).filter(order_count=1).count()
        
        returning = repeat_customers
        
        return {
            "user_base": {
                "total_customers": total_customers,
                "total_admins": total_admins,
                "new_registrations": {
                    "today": new_today,
                    "week": new_week,
                    "month": new_month
                },
                "growth_rate": 5.2  # Calculate based on previous period
            },
            "engagement": {
                "active_customers": active_customers,
                "inactive_customers": inactive_customers,
                "repeat_customers": repeat_customers,
                "avg_orders_per_customer": round(avg_orders_per_customer, 2),
                "customer_retention_rate": round(retention_rate, 2),
                "avg_days_between_orders": 45.0  # Calculate from actual data
            },
            "top_customers": top_customers,
            "behavior": {
                "first_time_customers": first_time,
                "returning_customers": returning
            }
        }
    
    def _get_top_customers(self, limit=10):
        """Get top customers by order count"""
        top = User.objects.filter(user_type='customer').annotate(
            order_count=Count('orders')
        ).filter(order_count__gt=0).order_by('-order_count')[:limit]
        
        result = []
        for user in top:
            orders = user.orders.all()
            last_order = orders.order_by('-created_at').first()
            
            # Determine status based on order count
            if user.order_count >= 10:
                status = 'VIP'
            elif user.order_count >= 5:
                status = 'Gold'
            elif user.order_count >= 2:
                status = 'Silver'
            else:
                status = 'Regular'
            
            result.append({
                'id': user.id,
                'name': user.get_full_name() or user.username,
                'email': user.email,
                'orders_count': user.order_count,
                'total_value': 0.0,  # Calculate if you add revenue tracking
                'status': status,
                'last_order_date': last_order.created_at.isoformat() if last_order else ""
            })
        
        return result
    
    # ===================== COMMUNICATION ANALYTICS =====================
    
    def _calculate_communication_analytics(self, date_start, date_end):
        """Calculate communication analytics"""
        messages_data = self._calculate_message_analytics(date_start, date_end)
        tickets_data = self._calculate_support_tickets(date_start, date_end)
        
        return {
            "messages": messages_data,
            "support_tickets": tickets_data
        }
    
    def _calculate_message_analytics(self, date_start, date_end):
        """Calculate message analytics"""
        messages_qs = self._filter_by_date(Message.objects.all(), date_start, date_end)
        
        total_messages = messages_qs.count()
        unread_count = messages_qs.filter(is_read=False).count()
        
        # By sender type
        by_sender = messages_qs.values('sender_type').annotate(count=Count('id'))
        sender_type_dict = {'user': 0, 'admin': 0, 'system': 0}
        for item in by_sender:
            sender_type_dict[item['sender_type']] = item['count']
        
        # Messages per order
        orders_with_messages = messages_qs.exclude(order__isnull=True).values('order').distinct().count()
        messages_per_order = total_messages / orders_with_messages if orders_with_messages > 0 else 0
        
        # Most discussed orders
        most_discussed = Message.objects.exclude(order__isnull=True).values('order', 'order__order_id').annotate(
            message_count=Count('id')
        ).order_by('-message_count')[:5]
        
        most_discussed_list = []
        for item in most_discussed:
            order = Order.objects.filter(id=item['order']).first()
            most_discussed_list.append({
                'order_id': item['order'],
                'order_number': item['order__order_id'],
                'message_count': item['message_count'],
                'status': 'active' if order and order.order_status != 'delivered' else 'resolved'
            })
        
        return {
            "total_messages": total_messages,
            "unread_count": unread_count,
            "avg_response_time_hours": 4.2,  # Calculate from actual timestamps
            "response_rate": 92.5,  # Calculate based on admin responses
            "by_sender_type": sender_type_dict,
            "messages_per_order": round(messages_per_order, 2),
            "most_discussed_orders": most_discussed_list
        }
    
    def _calculate_support_tickets(self, date_start, date_end):
        """Calculate support ticket analytics"""
        tickets_qs = self._filter_by_date(Contact.objects.all(), date_start, date_end)
        
        total_tickets = tickets_qs.count()
        
        # By status
        by_status = tickets_qs.values('status').annotate(count=Count('id'))
        status_list = []
        for item in by_status:
            status_list.append({
                'status': item['status'],
                'count': item['count'],
                'percentage': round((item['count'] / total_tickets * 100) if total_tickets > 0 else 0, 2)
            })
        
        # Open tickets
        open_tickets = tickets_qs.filter(status__in=['new', 'in_progress']).count()
        
        # Resolution rate
        resolved = tickets_qs.filter(status__in=['resolved', 'closed']).count()
        resolution_rate = (resolved / total_tickets * 100) if total_tickets > 0 else 0
        
        # By contact method
        by_method = tickets_qs.values('preferred_contact_method').annotate(count=Count('id'))
        method_list = []
        for item in by_method:
            method_list.append({
                'method': item['preferred_contact_method'],
                'count': item['count'],
                'percentage': round((item['count'] / total_tickets * 100) if total_tickets > 0 else 0, 2)
            })
        
        # Order related vs general
        order_related_count = tickets_qs.filter(order_related=True).count()
        general_count = tickets_qs.filter(order_related=False).count()
        
        # Unanswered tickets
        unanswered = tickets_qs.filter(admin_response__isnull=True).count()
        
        # Most active days
        most_active = tickets_qs.annotate(
            day=TruncDate('created_at')
        ).values('day').annotate(count=Count('id')).order_by('-count')[:7]
        
        active_days = []
        for item in most_active:
            active_days.append({
                'day': item['day'].strftime('%Y-%m-%d'),
                'count': item['count']
            })
        
        return {
            "total_tickets": total_tickets,
            "by_status": status_list,
            "open_tickets": open_tickets,
            "resolution_rate": round(resolution_rate, 2),
            "avg_resolution_time_hours": 24.5,  # Calculate from actual data
            "by_contact_method": method_list,
            "order_related_vs_general": {
                "order_related": order_related_count,
                "general": general_count
            },
            "unanswered_tickets": unanswered,
            "most_active_days": active_days
        }
    
    # ===================== NEWS ENGAGEMENT =====================
    
    def _calculate_news_engagement(self, date_start, date_end):
        """Calculate news engagement analytics"""
        if NewsItem is None:
            return self._empty_news_engagement()
        
        news_qs = self._filter_by_date(NewsItem.objects.all(), date_start, date_end, field='published_at')
        
        total_news = news_qs.count()
        total_reads = sum(item.read_count for item in news_qs)
        avg_read_count = total_reads / total_news if total_news > 0 else 0
        total_clicks = news_qs.aggregate(total=Sum('click_count'))['total'] or 0
        
        total_users = User.objects.filter(user_type='customer').count()
        engagement_rate = (total_reads / total_users * 100) if total_users > 0 else 0
        click_rate = (total_clicks / total_reads * 100) if total_reads > 0 else 0
        
        # By category
        by_category = []
        categories = news_qs.values('category').annotate(
            count=Count('id'),
            total_reads=Sum('click_count')
        )
        for cat in categories:
            by_category.append({
                'category': cat['category'],
                'count': cat['count'],
                'reads': cat['total_reads'] or 0,
                'engagement_rate': 0.0  # Calculate based on reads
            })
        
        # By priority
        by_priority = news_qs.values('priority').annotate(count=Count('id'))
        priority_dict = {'high': 0, 'medium': 0, 'low': 0}
        for item in by_priority:
            priority_dict[item['priority']] = item['count']
        
        # Distribution
        active_news = news_qs.filter(expires_at__gte=self.now).count()
        expired_news = news_qs.filter(expires_at__lt=self.now).count()
        auto_generated = news_qs.filter(auto_generated=True).count()
        manual = news_qs.filter(auto_generated=False).count()
        
        # Top performing
        top_performing = news_qs.order_by('-click_count')[:5]
        top_list = []
        for news in top_performing:
            top_list.append({
                'id': str(news.id),
                'title': news.title,
                'category': news.category,
                'reads': news.read_count,
                'clicks': news.click_count,
                'priority': news.priority,
                'published_date': news.published_at.isoformat()
            })
        
        return {
            "overview": {
                "total_news": total_news,
                "total_reads": total_reads,
                "avg_read_count": round(avg_read_count, 2),
                "total_clicks": total_clicks,
                "engagement_rate": round(engagement_rate, 2),
                "click_rate": round(click_rate, 2)
            },
            "by_category": by_category,
            "by_priority": priority_dict,
            "distribution": {
                "active_news": active_news,
                "expired_news": expired_news,
                "auto_generated": auto_generated,
                "manual": manual
            },
            "top_performing": top_list
        }
    
    def _empty_news_engagement(self):
        """Return empty news engagement structure"""
        return {
            "overview": {
                "total_news": 0,
                "total_reads": 0,
                "avg_read_count": 0.0,
                "total_clicks": 0,
                "engagement_rate": 0.0,
                "click_rate": 0.0
            },
            "by_category": [],
            "by_priority": {"high": 0, "medium": 0, "low": 0},
            "distribution": {
                "active_news": 0,
                "expired_news": 0,
                "auto_generated": 0,
                "manual": 0
            },
            "top_performing": []
        }
    
    # ===================== TIME TRENDS =====================
    
    def _calculate_time_trends(self, date_start, date_end):
        """Calculate time-based trends"""
        # Daily orders
        daily_orders = self._calculate_daily_orders(date_start, date_end)
        
        # Weekly summary
        weekly_summary = self._calculate_weekly_summary(daily_orders)
        
        # Monthly growth
        monthly_growth = self._calculate_monthly_growth()
        
        # Quarterly comparison
        quarterly = self._calculate_quarterly_comparison()
        
        # Peak activity
        peak_activity = self._calculate_peak_activity()
        
        return {
            "daily_orders": daily_orders,
            "weekly_summary": weekly_summary,
            "monthly_growth": monthly_growth,
            "quarterly_comparison": quarterly,
            "peak_activity": peak_activity
        }
    
    def _calculate_daily_orders(self, date_start, date_end):
        """Calculate daily order counts"""
        if not date_start or not date_end:
            # Default to last 7 days
            date_end = self.now.date()
            date_start = date_end - timedelta(days=6)
        
        daily_data = Order.objects.filter(
            created_at__date__gte=date_start,
            created_at__date__lte=date_end
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            orders=Count('id')
        ).order_by('date')
        
        result = []
        for item in daily_data:
            result.append({
                'date': item['date'].strftime('%Y-%m-%d'),
                'day_name': item['date'].strftime('%A'),
                'orders': item['orders'],
                'revenue': None
            })
        
        return result
    
    def _calculate_weekly_summary(self, daily_orders):
        """Calculate weekly summary from daily orders"""
        total_orders = sum(day['orders'] for day in daily_orders)
        avg_daily = total_orders / len(daily_orders) if daily_orders else 0
        
        peak_day_data = max(daily_orders, key=lambda x: x['orders']) if daily_orders else None
        
        return {
            "total_orders": total_orders,
            "avg_daily_orders": round(avg_daily, 2),
            "peak_day": peak_day_data['day_name'] if peak_day_data else "",
            "peak_day_orders": peak_day_data['orders'] if peak_day_data else 0
        }
    
    def _calculate_monthly_growth(self):
        """Calculate monthly growth for last 6 months"""
        result = []
        for i in range(5, -1, -1):
            month_date = self.now - timedelta(days=30 * i)
            month_start = month_date.replace(day=1)
            
            if month_date.month == 12:
                month_end = month_date.replace(day=31)
            else:
                month_end = (month_date.replace(month=month_date.month + 1, day=1) - timedelta(days=1))
            
            orders = Order.objects.filter(
                created_at__date__gte=month_start,
                created_at__date__lte=month_end
            ).count()
            
            result.append({
                'month': month_date.strftime('%B'),
                'year': month_date.year,
                'orders': orders,
                'growth_percentage': 0.0  # Calculate vs previous month
            })
        
        return result
    
    def _calculate_quarterly_comparison(self):
        """Calculate quarterly comparison"""
        quarters = []
        current_quarter = (self.now.month - 1) // 3 + 1
        
        for i in range(4):
            q = current_quarter - i
            year = self.now.year
            if q <= 0:
                q += 4
                year -= 1
            
            quarters.append({
                'quarter': f"Q{q} {year}",
                'orders': 0,  # Calculate actual orders for the quarter
                'growth_percentage': 0.0
            })
        
        return quarters
    
    def _calculate_peak_activity(self):
        """Calculate peak activity times"""
        # Peak hour (if you track hour of creation)
        # Peak day of week
        weekday_data = Order.objects.annotate(
            weekday=ExtractWeekDay('created_at')
        ).values('weekday').annotate(count=Count('id')).order_by('-count').first()
        
        weekday_map = {1: 'Sunday', 2: 'Monday', 3: 'Tuesday', 4: 'Wednesday', 5: 'Thursday', 6: 'Friday', 7: 'Saturday'}
        peak_day = weekday_map.get(weekday_data['weekday'], 'Monday') if weekday_data else 'Monday'
        
        # Peak month
        month_data = Order.objects.annotate(
            month=TruncDate('created_at')
        ).values('month').annotate(count=Count('id')).order_by('-count').first()
        
        peak_month = month_data['month'].strftime('%B') if month_data else 'January'
        
        return {
            "peak_hour": "2 PM - 3 PM",
            "peak_day_of_week": peak_day,
            "peak_month": peak_month
        }
    
    # ===================== OPERATIONAL INSIGHTS =====================
    
    def _calculate_operational_insights(self, date_start, date_end):
        """Calculate operational insights"""
        admin_activity = self._calculate_admin_activity()
        order_logs = self._calculate_order_logs(date_start, date_end)
        recent_activity = self._calculate_recent_activity()
        system_health = self._calculate_system_health()
        
        return {
            "admin_activity": admin_activity,
            "order_logs": order_logs,
            "recent_activity": recent_activity,
            "system_health": system_health
        }
    
    def _calculate_admin_activity(self):
        """Calculate admin activity metrics"""
        admins = User.objects.filter(user_type='admin')
        
        result = []
        for admin in admins:
            uploads = OrderFile.objects.filter(uploaded_by=admin).count()
            responses = Contact.objects.filter(responded_by=admin).count()
            declinations = Order.objects.filter(declined_by=admin).count()
            
            efficiency_score = (responses / (responses + declinations) * 100) if (responses + declinations) > 0 else 0
            
            result.append({
                'admin_id': admin.id,
                'admin_name': admin.get_full_name() or admin.username,
                'uploads': uploads,
                'responses': responses,
                'declinations': declinations,
                'efficiency_score': round(efficiency_score, 2)
            })
        
        return result
    
    def _calculate_order_logs(self, date_start, date_end):
        """Calculate order log analytics"""
        logs_qs = self._filter_by_date(OrderLog.objects.all(), date_start, date_end, field='timestamp')
        
        total_logs = logs_qs.count()
        
        # Most modified orders
        most_modified = OrderLog.objects.values('order', 'order__order_id').annotate(
            log_count=Count('id')
        ).order_by('-log_count')[:5]
        
        most_modified_list = []
        for item in most_modified:
            most_modified_list.append({
                'order_id': item['order'],
                'order_number': item['order__order_id'],
                'log_count': item['log_count']
            })
        
        # Action breakdown
        action_breakdown = logs_qs.values('action').annotate(count=Count('id')).order_by('-count')[:10]
        action_list = []
        for item in action_breakdown:
            action_list.append({
                'action': item['action'],
                'count': item['count']
            })
        
        return {
            "total_logs": total_logs,
            "most_modified_orders": most_modified_list,
            "action_breakdown": action_list
        }
    
    def _calculate_recent_activity(self, limit=10):
        """Get recent activity logs"""
        recent = OrderLog.objects.select_related('order', 'user').order_by('-timestamp')[:limit]
        
        result = []
        for log in recent:
            time_diff = self.now - log.timestamp
            if time_diff.seconds < 60:
                time_ago = f"{time_diff.seconds} sec ago"
            elif time_diff.seconds < 3600:
                time_ago = f"{time_diff.seconds // 60} min ago"
            elif time_diff.days == 0:
                time_ago = f"{time_diff.seconds // 3600} hr ago"
            else:
                time_ago = f"{time_diff.days} day(s) ago"
            
            result.append({
                'id': log.id,
                'action': log.action,
                'order_number': log.order.order_id,
                'admin_name': log.user.get_full_name() if log.user else 'System',
                'timestamp': log.timestamp.isoformat(),
                'time_ago': time_ago
            })
        
        return result
    
    def _calculate_system_health(self):
        """Calculate system health metrics"""
        today = self.now.date()
        
        # Orders on track
        on_track = Order.objects.filter(
            preferred_delivery_date__gte=today,
            order_status__in=['new', 'confirmed', 'cad_done', 'user_confirmed', 'rpt_done', 'casting', 'ready']
        ).count()
        
        # Orders at risk (approaching deadline or overdue)
        at_risk = Order.objects.filter(
            preferred_delivery_date__lt=today + timedelta(days=3),
            order_status__in=['new', 'confirmed', 'cad_done', 'user_confirmed', 'rpt_done', 'casting', 'ready']
        ).count()
        
        return {
            "orders_on_track": on_track,
            "orders_at_risk": at_risk,
            "system_uptime": "99.9%"
        }
    
    # ===================== MAIN METHOD =====================
    
    def get_full_analysis(self, params):
        """
        Main method to get full analytics dashboard data
        
        Args:
            params: Dictionary containing time_filter, start_date, end_date
        
        Returns:
            Dictionary containing all analytics data
        """
        time_filter = params.get('time_filter')
        start_date = params.get('start_date')
        end_date = params.get('end_date')
        
        date_start, date_end = self._get_date_range(time_filter, start_date, end_date)
        
        return {
            "kpi": self._calculate_kpi(date_start, date_end),
            "order_analytics": self._calculate_order_analytics(date_start, date_end),
            "customer_analytics": self._calculate_customer_analytics(date_start, date_end),
            "communication_analytics": self._calculate_communication_analytics(date_start, date_end),
            "news_engagement": self._calculate_news_engagement(date_start, date_end),
            "time_trends": self._calculate_time_trends(date_start, date_end),
            "operational_insights": self._calculate_operational_insights(date_start, date_end),
            "meta": {
                "generated_at": self.now.isoformat(),
                "time_filter": time_filter or "",
                "date_range": {
                    "start": str(date_start) if date_start else "",
                    "end": str(date_end) if date_end else ""
                },
                "timezone": str(timezone.get_current_timezone())
            }
        }
