from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def health_check(request):
    """Health check endpoint for Railway"""
    return JsonResponse({
        'status': 'success',
        'message': 'QLDT Web API is running',
        'version': '1.0.0'
    })

def home(request):
    """Home page"""
    return JsonResponse({
        'message': 'Welcome to QLDT Web API',
        'endpoints': {
            'health': '/',
            'api': '/api/',
            'products': '/api/products/'
        }
    })