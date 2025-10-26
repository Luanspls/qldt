import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'QldtWeb.settings')
django.setup()

from django.conf import settings

print("=== CURRENT DATABASE CONFIG ===")
db_config = settings.DATABASES['default']
print(f"ENGINE: {db_config['ENGINE']}")
print(f"NAME: {db_config['NAME']}")
print(f"HOST: {db_config['HOST']}")
print(f"PORT: {db_config['PORT']}")
print(f"USER: {db_config['USER']}")

# Test connection
from django.db import connection
try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
    print("✅ Database connection successful")
except Exception as e:
    print(f"❌ Database connection failed: {e}")