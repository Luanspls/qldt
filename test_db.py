import os
import django
from django.core.management import execute_from_command_line

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'QldtWeb.settings')
django.setup()

from django.db import connection
from django.contrib.auth.models import User

try:
    # Test database connection
    connection.ensure_connection()
    print("✅ Database connection successful!")
    
    # Test if auth tables exist
    user_count = User.objects.count()
    print(f"✅ Auth tables exist. Users count: {user_count}")
    
    # Test creating a user (if none exist)
    if user_count == 0:
        User.objects.create_user('testuser', 'test@example.com', 'testpass123')
        print("✅ Test user created successfully!")
        
except Exception as e:
    print(f"❌ Database error: {e}")
    import traceback
    traceback.print_exc()