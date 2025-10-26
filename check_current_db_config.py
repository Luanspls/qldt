import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'QldtWeb.settings')
django.setup()

from django.conf import settings

print("=== CURRENT DATABASE CONFIG ===")
db_config = settings.DATABASES['default']
print(f"ENGINE: {db_config['ENGINE']}")
print(f"HOST: {db_config.get('HOST', 'N/A')}")
print(f"NAME: {db_config.get('NAME', 'N/A')}")
print(f"USER: {db_config.get('USER', 'N/A')}")

# Kiểm tra environment variables
print("\n=== ENVIRONMENT VARIABLES ===")
print(f"DATABASE_URL: {os.environ.get('DATABASE_URL', 'NOT SET')}")
print(f"DB_HOST: {os.environ.get('DB_HOST', 'NOT SET')}")

# Test connection
from django.db import connection
try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
    print(f"✅ Database connection: {result}")
except Exception as e:
    print(f"❌ Database connection failed: {e}")