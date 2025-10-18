from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from analytics.services.dashboard_service import DashboardAnalyticsService
from analytics.serializers import (
    DashboardAnalyticsSerializer, 
    DateRangeInputSerializer
)


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
