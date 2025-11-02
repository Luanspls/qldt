import os
import django
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'QldtWeb.settings')

try:
    django.setup()
    print("✓ Django setup successful")
    
    # Test database
    from django.db import connection
    connection.ensure_connection()
    print("✓ Database connection successful")
    
    # Test models
    from products.models import Department
    print("✓ Models import successful")
    
    # Test URLs
    from django.core.handlers.wsgi import WSGIHandler
    application = WSGIHandler()
    print("✓ WSGI handler successful")
    
    # Test middleware
    from django.test import RequestFactory
    factory = RequestFactory()
    request = factory.get('/')
    
    from django.contrib.sessions.middleware import SessionMiddleware
    middleware = SessionMiddleware(lambda x: x)
    middleware.process_request(request)
    print("✓ Middleware successful")
    
    print("🎉 ALL TESTS PASSED - Application should work!")
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    print("FULL TRACEBACK:")
    traceback.print_exc()