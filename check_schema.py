import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'QldtWeb.settings')
django.setup()

from django.db import connection
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.contrib.contenttypes.models import ContentType

try:
    # Kiểm tra các bảng quan trọng
    print("✅ Checking database tables...")
    
    with connection.cursor() as cursor:
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Available tables: {tables}")
    
    # Kiểm tra các model quan trọng
    print(f"✅ Users count: {User.objects.count()}")
    print(f"✅ Sessions count: {Session.objects.count()}")
    print(f"✅ ContentTypes count: {ContentType.objects.count()}")
    
    # Kiểm tra user admin
    admin_user = User.objects.filter(username='admin').first()
    if admin_user:
        print(f"✅ Admin user: {admin_user.username}")
        print(f"✅ Admin is_staff: {admin_user.is_staff}")
        print(f"✅ Admin is_superuser: {admin_user.is_superuser}")
    else:
        print("❌ Admin user not found")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()