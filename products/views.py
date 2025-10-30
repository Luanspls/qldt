from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.shortcuts import render
from .services import UserService
from .supabase_api import supabase_api


# @csrf_exempt
# def users_list(request):
#     if request.method == 'GET':
#         try:
#             users = UserService.get_all_users()
#             return JsonResponse(users, safe=False)
#         except Exception as e:
#             return JsonResponse({'error': str(e)}, status=500)
    
#     elif request.method == 'POST':
#         try:
#             data = json.loads(request.body)
#             user = UserService.create_user(data)
#             return JsonResponse(user, status=201)
#         except Exception as e:
#             return JsonResponse({'error': str(e)}, status=400)

# @csrf_exempt
# def user_detail(request, user_id):
#     if request.method == 'GET':
#         try:
#             user = UserService.get_user_by_id(user_id)
#             if user:
#                 return JsonResponse(user)
#             return JsonResponse({'error': 'user not found'}, status=404)
#         except Exception as e:
#             return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def users_list(request):
    if request.method == 'GET':
        users = supabase_api.get_users()
        return JsonResponse(users, safe=False)
    
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            user = supabase_api.create_user(data)
            if user:
                return JsonResponse(user, status=201)
            return JsonResponse({'error': 'Failed to create product'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def health_check(request):
    """Health check với Supabase connection test"""
    try:
        # Test Supabase connection
        users = supabase_api.get_users()
        return JsonResponse({
            'status': 'healthy',
            'database': 'supabase_connected',
            'supabase_items': len(users)
        })
    except Exception as e:
        return JsonResponse({
            'status': 'healthy',
            'database': 'supabase_disconnected',
            'error': str(e)
        })

def home_page(request):
    return render(request, 'products/home.html')

@csrf_exempt
def debug_setup(request):
    """Endpoint để debug và setup database"""
    try:
        from django.core.management import execute_from_command_line
        execute_from_command_line(['manage.py', 'migrate'])
        
        from django.contrib.auth.models import User
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin1', 'admin1@example.com', 'admin123')
            return JsonResponse({'status': 'success', 'message': 'Migrations run and admin user created'})
        else:
            return JsonResponse({'status': 'success', 'message': 'Migrations run - admin exists'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

from django.shortcuts import render
from django.views import View
from django.http import JsonResponse
import json

class TrainProgramManagerView(View):
    template_name = 'products/TrainProgram.html'
    
    def get(self, request):
        # Dữ liệu mẫu cho các dropdown
        context = {
            'khoa_dao_tao_list': [
                'Khoa Công nghệ Thông tin',
                'Khoa Kinh tế - Kế toán',
                'Khoa Ngoại ngữ',
                'Khoa Đào tạo Giáo viên',
                'Khoa các BMC'
            ],
            'to_bo_mon_list': [
                'Tổ Tin học',
                'Tổ Toán',
                'Tổ Cơ bản'
            ],
            'chuong_trinh_dao_tao_list': [
                'Chương trình Tin học ứng dụng',
                'Chương trình Quản trị mạng',
                'Chương trình Lập trình ứng dụng'
            ],
            'khoa_hoc_list': [
                'Khóa 2022-2025',
                'Khóa 2021-2024',
                'Khóa 2023-2026'
            ],
            'mon_hoc_data': self.get_sample_data()
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        # Xử lý thêm môn học mới
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            data = json.loads(request.body)
            # Xử lý dữ liệu ở đây
            return JsonResponse({'status': 'success', 'message': 'Đã thêm môn học thành công'})
        
        return JsonResponse({'status': 'error', 'message': 'Invalid request'})
    
    def put(self, request, id):
        # Xử lý cập nhật môn học
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            data = json.loads(request.body)
            # Xử lý cập nhật dữ liệu
            return JsonResponse({'status': 'success', 'message': 'Đã cập nhật môn học thành công'})
        
        return JsonResponse({'status': 'error', 'message': 'Invalid request'})
    
    def get_sample_data(self):
        # Dữ liệu mẫu cho bảng môn học
        return [
            {
                'id': 1,
                'ma_mon_hoc': 'MH01',
                'ten_mon_hoc': 'Giáo dục chính trị',
                'so_tin_chi': 4.0,
                'tong_so_gio': 75.0,
                'ly_thuyet': 41.0,
                'thuc_hanh': 29.0,
                'kiem_tra_thi': 5.0,
                'hk1': 4.0,
                'hk2': '',
                'hk3': '',
                'hk4': '',
                'hk5': '',
                'hk6': '',
                'don_vi': 'Khoa các BMC',
                'giang_vien': ''
            },
            {
                'id': 2,
                'ma_mon_hoc': 'MH02',
                'ten_mon_hoc': 'Pháp luật',
                'so_tin_chi': 2.0,
                'tong_so_gio': 30.0,
                'ly_thuyet': 18.0,
                'thuc_hanh': 10.0,
                'kiem_tra_thi': 2.0,
                'hk1': '',
                'hk2': '',
                'hk3': '',
                'hk4': '',
                'hk5': 2.0,
                'hk6': '',
                'don_vi': 'Khoa các BMC',
                'giang_vien': ''
            },
            {
                'id': 3,
                'ma_mon_hoc': 'MH03',
                'ten_mon_hoc': 'Giáo dục thể chất',
                'so_tin_chi': 2.0,
                'tong_so_gio': 60.0,
                'ly_thuyet': 5.0,
                'thuc_hanh': 51.0,
                'kiem_tra_thi': 4.0,
                'hk1': '',
                'hk2': 2.0,
                'hk3': '',
                'hk4': '',
                'hk5': '',
                'hk6': '',
                'don_vi': 'Khoa các BMC',
                'giang_vien': ''
            },
            {
                'id': 4,
                'ma_mon_hoc': 'MH04',
                'ten_mon_hoc': 'GD Quốc phòng và An ninh',
                'so_tin_chi': 3.0,
                'tong_so_gio': 75.0,
                'ly_thuyet': 36.0,
                'thuc_hanh': 36.0,
                'kiem_tra_thi': 3.0,
                'hk1': '',
                'hk2': '',
                'hk3': 3.0,
                'hk4': '',
                'hk5': '',
                'hk6': '',
                'don_vi': 'Khoa các BMC',
                'giang_vien': ''
            },
            {
                'id': 5,
                'ma_mon_hoc': 'MH05',
                'ten_mon_hoc': 'Tin học',
                'so_tin_chi': 3.0,
                'tong_so_gio': 75.0,
                'ly_thuyet': 15.0,
                'thuc_hanh': 58.0,
                'kiem_tra_thi': 2.0,
                'hk1': 3.0,
                'hk2': '',
                'hk3': '',
                'hk4': '',
                'hk5': '',
                'hk6': '',
                'don_vi': 'Tổ Tin học',
                'giang_vien': 'Trương Quỳnh Liễu'
            }
        ]

class ImportExcelView(View):
    def post(self, request):
        # Xử lý import file Excel
        if request.FILES.get('excel_file'):
            excel_file = request.FILES['excel_file']
            # Xử lý file Excel ở đây
            # Có thể sử dụng thư viện như pandas, openpyxl, etc.
            
            return JsonResponse({
                'status': 'success', 
                'message': 'Import file Excel thành công',
                'data': []  # Trả về dữ liệu đã import
            })
        
        return JsonResponse({'status': 'error', 'message': 'Không tìm thấy file'})

class ThongKeView(View):
    def get(self, request):
        # API trả về thống kê
        thong_ke = {
            'tong_tin_chi': 76.0,
            'tong_gio': 2475.0,
            'ty_le_ly_thuyet': '30.5%',
            'ty_le_thuc_hanh': '69.5%'
        }
        return JsonResponse(thong_ke)
