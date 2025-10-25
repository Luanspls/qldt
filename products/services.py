from supabase import create_client
import os
from typing import List, Dict, Optional

class UserService:
    @staticmethod
    def get_client():
        url = os.environ.get('SUPABASE_URL')
        key = os.environ.get('SUPABASE_KEY')
        return create_client(url, key)
    
    @staticmethod
    def get_all_users() -> List[Dict]:
        try:
            client = UserService.get_client()
            response = client.table('users').select('*').execute()
            return response.data
        except Exception as e:
            print(f"Error fetching users: {e}")
            return []
    
    @staticmethod
    def get_user_by_id(product_id: str) -> Optional[Dict]:
        try:
            client = UserService.get_client()
            response = client.table('users').select('*').eq('id', product_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error fetching user: {e}")
            return None
    
    @staticmethod
    def create_user(product_data: Dict) -> Optional[Dict]:
        try:
            client = UserService.get_client()
            response = client.table('users').insert(product_data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"Error creating user: {e}")
            return None