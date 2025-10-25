# products/views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .services import UserService

@csrf_exempt
def users_list(request):
    if request.method == 'GET':
        try:
            users = UserService.get_all_users()
            return JsonResponse(users, safe=False)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            user = UserService.create_user(data)
            return JsonResponse(user, status=201)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def user_detail(request, user_id):
    if request.method == 'GET':
        try:
            user = UserService.get_user_by_id(user_id)
            if user:
                return JsonResponse(user)
            return JsonResponse({'error': 'user not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def health_check(request):
    return JsonResponse({'status': 'ok'})