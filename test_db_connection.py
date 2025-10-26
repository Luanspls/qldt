import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'QldtWeb.settings')

try:
    import django
    django.setup()
    
    from django.db import connection
    print("Testing database connection...")
    
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        print(f"✅ Database connection successful: {result}")
        
    # Test auth tables
    from django.contrib.auth.models import User
    user_count = User.objects.count()
    print(f"✅ Users in database: {user_count}")
    
except Exception as e:
    print(f"❌ Database connection failed: {e}")
    print("\nTroubleshooting steps:")
    print("1. Check Supabase Allowed IPs - add 0.0.0.0/0")
    print("2. Verify DB_PASSWORD is correct")
    print("3. Check DB_HOST format (should be: db.xxx.supabase.co)")