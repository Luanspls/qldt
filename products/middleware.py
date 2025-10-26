from django.db import DatabaseError, connection
from django.http import JsonResponse
import logging

logger = logging.getLogger(__name__)

class DatabaseHealthCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Kiểm tra kết nối database trước mỗi request
        if request.path.startswith('/admin/'):
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    logger.info("✅ Database connection healthy for admin request")
            except DatabaseError as e:
                logger.error(f"❌ Database connection failed for admin: {e}")
                return JsonResponse({
                    'error': 'Database connection failed',
                    'details': str(e)
                }, status=500)
        
        response = self.get_response(request)
        return response