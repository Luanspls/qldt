import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'QldtWeb.settings')
django.setup()

from django.contrib.auth import authenticate, login
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware

def test_admin_login():
    # Tạo request giả lập
    factory = RequestFactory()
    request = factory.get('/admin/')
    
    # Thêm session
    middleware = SessionMiddleware(lambda x: None)
    middleware.process_request(request)
    request.session.save()
    
    # Test authentication
    user = authenticate(username='admin', password='c10.123456@')
    if user:
        print(f"✅ Authentication successful: {user}")
        login(request, user)
        print(f"✅ Login successful")
        print(f"✅ User is authenticated: {request.user.is_authenticated}")
    else:
        print("❌ Authentication failed")

if __name__ == '__main__':
    test_admin_login()