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
