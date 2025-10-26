import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'QldtWeb.settings')
django.setup()

from django.contrib.auth.models import User

try:
    # Xóa user admin cũ nếu tồn tại
    User.objects.filter(username='admin2').delete()
    
    # Tạo superuser mới
    user = User.objects.create_superuser(
        username='admin2',
        email='admin2@example.com',
        password='admin123456'
    )
    print(f"✅ Created new admin user: {user.username}")
except Exception as e:
    print(f"❌ Error creating admin: {e}")