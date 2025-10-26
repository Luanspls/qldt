import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

try:
    conn = psycopg2.connect(
        host=os.environ.get('DB_HOST'),
        port=os.environ.get('DB_PORT', 5432),
        database=os.environ.get('DB_NAME'),
        user=os.environ.get('DB_USER'),
        password=os.environ.get('DB_PASSWORD'),
        sslmode='require'
    )
    print("✅ Kết nối thành công!")
    conn.close()
except Exception as e:
    print(f"❌ Lỗi kết nối: {e}")