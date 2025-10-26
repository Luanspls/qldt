import os
import django
import sys

# Thiết lập Django environment TRƯỚC KHI import bất kỳ module Django nào
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'QldtWeb.settings')

# Setup Django
django.setup()

# BÂY GIỜ mới import các module Django
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.middleware import AuthenticationMiddleware

def check_middleware():
    print("✅ Django setup completed successfully")
    
    factory = RequestFactory()
    request = factory.get('/admin/')
    
    # Add session
    session_middleware = SessionMiddleware(lambda x: None)
    session_middleware.process_request(request)
    request.session.save()
    
    # Add authentication
    auth_middleware = AuthenticationMiddleware(lambda x: None)
    auth_middleware.process_request(request)
    
    # Test authentication
    from django.contrib.auth import authenticate, login
    user = authenticate(username='admin', password='c10.123456@')  # Thay 'your-password' bằng password thực
    
    if user:
        login(request, user)
        print(f"✅ User is authenticated: {request.user.is_authenticated}")
        print(f"✅ User: {request.user}")
        print(f"✅ User is staff: {request.user.is_staff}")
        print(f"✅ User is superuser: {request.user.is_superuser}")
    else:
        print("❌ Authentication failed - check username and password")

if __name__ == '__main__':
    check_middleware()