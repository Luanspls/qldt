import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


def health_check(request):
    return JsonResponse({
        'status': 'healthy',
        'service': 'Django API',
        'version': '1.0.0',
        'environment': os.getenv('ENVIRONMENT', 'development'),
        'public_url': f"https://{os.getenv('RAILWAY_PUBLIC_DOMAIN', 'localhost')}"},
        status=200
    )