import os
import django
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.middleware import AuthenticationMiddleware

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'QldtWeb.settings')
django.setup()

def test_admin_in_context():
    print("=== TESTING ADMIN LOGIN IN FULL CONTEXT ===")
    
    factory = RequestFactory()
    request = factory.post('/admin/login/', {
        'username': 'admin',
        'password': 'c10.54321@'  # THAY THẾ
    })
    
    # Add all middleware
    session_middleware = SessionMiddleware(lambda x: None)
    session_middleware.process_request(request)
    request.session.save()
    
    auth_middleware = AuthenticationMiddleware(lambda x: None)
    auth_middleware.process_request(request)
    
    # Test database connection in this context
    from django.db import connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
        print(f"✅ Database connection in context: {result}")
        
        # Test authentication
        from django.contrib.auth import authenticate
        user = authenticate(request, username='admin', password='your-actual-password')
        if user:
            print(f"✅ Authentication successful: {user}")
        else:
            print("❌ Authentication failed")
            
    except Exception as e:
        print(f"❌ Database connection failed in context: {e}")

if __name__ == '__main__':
    test_admin_in_context()