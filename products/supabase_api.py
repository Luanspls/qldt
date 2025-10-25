import requests
import os
from typing import List, Dict, Optional

class SupabaseAPI:
    def __init__(self):
        self.url = os.environ.get('SUPABASE_URL')
        self.key = os.environ.get('SUPABASE_ANON_KEY')
        self.headers = {
            'apikey': self.key,
            'Authorization': f'Bearer {self.key}',
            'Content-Type': 'application/json'
        }
    
    def get_users(self) -> List[Dict]:
        """Lấy danh sách products từ Supabase"""
        try:
            response = requests.get(
                f"{self.url}/rest/v1/products",
                headers=self.headers,
                params={"select": "*"}
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Supabase API Error: {e}")
            return []
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        try:
            response = requests.get(
                f"{self.url}/rest/v1/users",
                headers=self.headers,
                params={"select": "*"}
            )
            response.raise_for_status()
            return response.json()[0] if response.json() else None
        except Exception as e:
            print(f"Error fetching user: {e}")
            return None
    
    def create_user(self, user_data: Dict) -> Optional[Dict]:
        """Tạo product mới trên Supabase"""
        try:
            response = requests.post(
                f"{self.url}/rest/v1/users",
                headers=self.headers,
                json=user_data
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Supabase API Error: {e}")
            return None

# Singleton instance
supabase_api = SupabaseAPI()