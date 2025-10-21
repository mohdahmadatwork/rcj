from rest_framework import serializers


class DashboardAnalyticsSerializer(serializers.Serializer):
    """
    Serializer for dashboard analytics data.
    """
    period = serializers.DictField()
    overview_metrics = serializers.DictField()
    order_status_distribution = serializers.DictField()
    order_trends = serializers.DictField()
    recent_orders = serializers.ListField()
    deliveries_today = serializers.DictField()
    communication_stats = serializers.DictField()
    this_month_summary = serializers.DictField()
    alerts = serializers.ListField()


class DateRangeInputSerializer(serializers.Serializer):
    """
    Serializer for validating date range inputs.
    """
    start_date = serializers.DateField(
        required=False, 
        help_text="Start date in YYYY-MM-DD format"
    )
    end_date = serializers.DateField(
        required=False, 
        help_text="End date in YYYY-MM-DD format"
    )
    period = serializers.ChoiceField(
        choices=['today', 'week', 'month', 'quarter', 'year'],
        required=False,
        help_text="Predefined period"
    )
    
    def validate(self, data):
        """
        Check that start_date is before end_date if both provided.
        """
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if start_date and end_date:
            if start_date > end_date:
                raise serializers.ValidationError(
                    "end_date must be after start_date"
                )
        
        return data


# analytics/serializers.py
from rest_framework import serializers


# ============= KPI Serializers =============
class KPIItemSerializer(serializers.Serializer):
    value = serializers.CharField()
    change_percentage = serializers.FloatField()
    change_label = serializers.CharField()


class KPIOverviewSerializer(serializers.Serializer):
    total_orders = KPIItemSerializer()
    active_customers = KPIItemSerializer()
    avg_completion_time = KPIItemSerializer()
    support_resolution_rate = KPIItemSerializer()
    completion_rate = KPIItemSerializer()
    pending_approvals = KPIItemSerializer()


# ============= Order Analytics Serializers =============
class StatusDistributionSerializer(serializers.Serializer):
    status = serializers.CharField()
    count = serializers.IntegerField()
    percentage = serializers.FloatField()


class StagePerformanceSerializer(serializers.Serializer):
    stage = serializers.CharField()
    avg_time_days = serializers.FloatField()
    avg_time_label = serializers.CharField()
    status = serializers.CharField()


class GoldColorSerializer(serializers.Serializer):
    color = serializers.CharField()
    count = serializers.IntegerField()
    percentage = serializers.FloatField()


class DiamondSizeDistributionSerializer(serializers.Serializer):
    range = serializers.CharField()
    count = serializers.IntegerField()


class DiamondSizesSerializer(serializers.Serializer):
    avg_size = serializers.FloatField()
    min_size = serializers.FloatField()
    max_size = serializers.FloatField()
    distribution = DiamondSizeDistributionSerializer(many=True)


class GoldWeightsSerializer(serializers.Serializer):
    avg_weight = serializers.FloatField()
    total_weight = serializers.FloatField()


class ProductPreferencesSerializer(serializers.Serializer):
    gold_colors = GoldColorSerializer(many=True)
    diamond_sizes = DiamondSizesSerializer()
    gold_weights = GoldWeightsSerializer()
    special_requirements_count = serializers.IntegerField()


class FileActivitySerializer(serializers.Serializer):
    stage = serializers.CharField()
    count = serializers.IntegerField()
    percentage = serializers.FloatField()


class TimelineAlertsSerializer(serializers.Serializer):
    same_day_orders = serializers.IntegerField()
    approaching_deadline = serializers.IntegerField()
    overdue_orders = serializers.IntegerField()


class OrderAnalyticsSerializer(serializers.Serializer):
    status_distribution = StatusDistributionSerializer(many=True)
    completed_orders = serializers.IntegerField()
    pending_approvals = serializers.IntegerField()
    declined_orders = serializers.IntegerField()
    stage_performance = StagePerformanceSerializer(many=True)
    product_preferences = ProductPreferencesSerializer()
    file_activity = FileActivitySerializer(many=True)
    timeline_alerts = TimelineAlertsSerializer()


# ============= Customer Analytics Serializers =============
class NewRegistrationsSerializer(serializers.Serializer):
    today = serializers.IntegerField()
    week = serializers.IntegerField()
    month = serializers.IntegerField()


class UserBaseSerializer(serializers.Serializer):
    total_customers = serializers.IntegerField()
    total_admins = serializers.IntegerField()
    new_registrations = NewRegistrationsSerializer()
    growth_rate = serializers.FloatField()


class EngagementSerializer(serializers.Serializer):
    active_customers = serializers.IntegerField()
    inactive_customers = serializers.IntegerField()
    repeat_customers = serializers.IntegerField()
    avg_orders_per_customer = serializers.FloatField()
    customer_retention_rate = serializers.FloatField()
    avg_days_between_orders = serializers.FloatField()


class TopCustomerSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    email = serializers.CharField()
    orders_count = serializers.IntegerField()
    total_value = serializers.FloatField()
    status = serializers.CharField()
    last_order_date = serializers.CharField()


class BehaviorSerializer(serializers.Serializer):
    first_time_customers = serializers.IntegerField()
    returning_customers = serializers.IntegerField()


class CustomerAnalyticsSerializer(serializers.Serializer):
    user_base = UserBaseSerializer()
    engagement = EngagementSerializer()
    top_customers = TopCustomerSerializer(many=True)
    behavior = BehaviorSerializer()


# ============= Communication Analytics Serializers =============
class BySenderTypeSerializer(serializers.Serializer):
    user = serializers.IntegerField()
    admin = serializers.IntegerField()
    system = serializers.IntegerField()


class MostDiscussedOrderSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    order_number = serializers.CharField()
    message_count = serializers.IntegerField()
    status = serializers.CharField()


class MessagesSerializer(serializers.Serializer):
    total_messages = serializers.IntegerField()
    unread_count = serializers.IntegerField()
    avg_response_time_hours = serializers.FloatField()
    response_rate = serializers.FloatField()
    by_sender_type = BySenderTypeSerializer()
    messages_per_order = serializers.FloatField()
    most_discussed_orders = MostDiscussedOrderSerializer(many=True)


class ByStatusSerializer(serializers.Serializer):
    status = serializers.CharField()
    count = serializers.IntegerField()
    percentage = serializers.FloatField()


class ByContactMethodSerializer(serializers.Serializer):
    method = serializers.CharField()
    count = serializers.IntegerField()
    percentage = serializers.FloatField()


class OrderRelatedVsGeneralSerializer(serializers.Serializer):
    order_related = serializers.IntegerField()
    general = serializers.IntegerField()


class MostActiveDaySerializer(serializers.Serializer):
    day = serializers.CharField()
    count = serializers.IntegerField()


class SupportTicketsSerializer(serializers.Serializer):
    total_tickets = serializers.IntegerField()
    by_status = ByStatusSerializer(many=True)
    open_tickets = serializers.IntegerField()
    resolution_rate = serializers.FloatField()
    avg_resolution_time_hours = serializers.FloatField()
    by_contact_method = ByContactMethodSerializer(many=True)
    order_related_vs_general = OrderRelatedVsGeneralSerializer()
    unanswered_tickets = serializers.IntegerField()
    most_active_days = MostActiveDaySerializer(many=True)


class CommunicationAnalyticsSerializer(serializers.Serializer):
    messages = MessagesSerializer()
    support_tickets = SupportTicketsSerializer()


# ============= News Engagement Serializers =============
class NewsOverviewSerializer(serializers.Serializer):
    total_news = serializers.IntegerField()
    total_reads = serializers.IntegerField()
    avg_read_count = serializers.FloatField()
    total_clicks = serializers.IntegerField()
    engagement_rate = serializers.FloatField()
    click_rate = serializers.FloatField()


class NewsByCategorySerializer(serializers.Serializer):
    category = serializers.CharField()
    count = serializers.IntegerField()
    reads = serializers.IntegerField()
    engagement_rate = serializers.FloatField()


class NewsByPrioritySerializer(serializers.Serializer):
    high = serializers.IntegerField()
    medium = serializers.IntegerField()
    low = serializers.IntegerField()


class NewsDistributionSerializer(serializers.Serializer):
    active_news = serializers.IntegerField()
    expired_news = serializers.IntegerField()
    auto_generated = serializers.IntegerField()
    manual = serializers.IntegerField()


class TopPerformingNewsSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()
    category = serializers.CharField()
    reads = serializers.IntegerField()
    clicks = serializers.IntegerField()
    priority = serializers.CharField()
    published_date = serializers.CharField()


class NewsEngagementSerializer(serializers.Serializer):
    overview = NewsOverviewSerializer()
    by_category = NewsByCategorySerializer(many=True)
    by_priority = NewsByPrioritySerializer()
    distribution = NewsDistributionSerializer()
    top_performing = TopPerformingNewsSerializer(many=True)


# ============= Time Trends Serializers =============
class DailyOrderSerializer(serializers.Serializer):
    date = serializers.CharField()
    day_name = serializers.CharField()
    orders = serializers.IntegerField()
    revenue = serializers.FloatField(required=False, allow_null=True)


class WeeklySummarySerializer(serializers.Serializer):
    total_orders = serializers.IntegerField()
    avg_daily_orders = serializers.FloatField()
    peak_day = serializers.CharField()
    peak_day_orders = serializers.IntegerField()


class MonthlyGrowthSerializer(serializers.Serializer):
    month = serializers.CharField()
    year = serializers.IntegerField()
    orders = serializers.IntegerField()
    growth_percentage = serializers.FloatField()


class QuarterlyComparisonSerializer(serializers.Serializer):
    quarter = serializers.CharField()
    orders = serializers.IntegerField()
    growth_percentage = serializers.FloatField()


class PeakActivitySerializer(serializers.Serializer):
    peak_hour = serializers.CharField()
    peak_day_of_week = serializers.CharField()
    peak_month = serializers.CharField()


class TimeTrendsSerializer(serializers.Serializer):
    daily_orders = DailyOrderSerializer(many=True)
    weekly_summary = WeeklySummarySerializer()
    monthly_growth = MonthlyGrowthSerializer(many=True)
    quarterly_comparison = QuarterlyComparisonSerializer(many=True)
    peak_activity = PeakActivitySerializer()


# ============= Operational Insights Serializers =============
class AdminActivitySerializer(serializers.Serializer):
    admin_id = serializers.IntegerField()
    admin_name = serializers.CharField()
    uploads = serializers.IntegerField()
    responses = serializers.IntegerField()
    declinations = serializers.IntegerField()
    efficiency_score = serializers.FloatField()


class MostModifiedOrderSerializer(serializers.Serializer):
    order_id = serializers.IntegerField()
    order_number = serializers.CharField()
    log_count = serializers.IntegerField()


class ActionBreakdownSerializer(serializers.Serializer):
    action = serializers.CharField()
    count = serializers.IntegerField()


class OrderLogsSerializer(serializers.Serializer):
    total_logs = serializers.IntegerField()
    most_modified_orders = MostModifiedOrderSerializer(many=True)
    action_breakdown = ActionBreakdownSerializer(many=True)


class RecentActivitySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    action = serializers.CharField()
    order_number = serializers.CharField()
    admin_name = serializers.CharField()
    timestamp = serializers.CharField()
    time_ago = serializers.CharField()


class SystemHealthSerializer(serializers.Serializer):
    orders_on_track = serializers.IntegerField()
    orders_at_risk = serializers.IntegerField()
    system_uptime = serializers.CharField()


class OperationalInsightsSerializer(serializers.Serializer):
    admin_activity = AdminActivitySerializer(many=True)
    order_logs = OrderLogsSerializer()
    recent_activity = RecentActivitySerializer(many=True)
    system_health = SystemHealthSerializer()


# ============= Meta Serializers =============
class DateRangeSerializer(serializers.Serializer):
    start = serializers.CharField()
    end = serializers.CharField()


class MetaSerializer(serializers.Serializer):
    generated_at = serializers.CharField()
    time_filter = serializers.CharField()
    date_range = DateRangeSerializer()
    timezone = serializers.CharField()


# ============= Main Response Serializer =============
class AnalyticsDashboardResponseSerializer(serializers.Serializer):
    kpi = KPIOverviewSerializer()
    order_analytics = OrderAnalyticsSerializer()
    customer_analytics = CustomerAnalyticsSerializer()
    communication_analytics = CommunicationAnalyticsSerializer()
    news_engagement = NewsEngagementSerializer()
    time_trends = TimeTrendsSerializer()
    operational_insights = OperationalInsightsSerializer()
    meta = MetaSerializer()
