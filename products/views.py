from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.shortcuts import render, get_object_or_404
from django.views import View
from .models import Department, SubjectGroup, Curriculum, Course, Subject, SubjectType, SemesterAllocation, Major, ImportHistory
from django.db.models import Q
import pandas as pd
from django.core.files.storage import default_storage
import os
from django.conf import settings
from .services import UserService
from .supabase_api import supabase_api
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required


def home_page(request):
    return render(request, 'products/home.html')

def users_list(request):
    users = supabase_api.get_users()
    return JsonResponse(users, safe=False)    

class TrainProgramManagerView(View):
    template_name = 'products/TrainProgram.html'
    
    def get(self, request):
        try:
            # Lấy dữ liệu từ database
            departments = Department.objects.all().values('id', 'code', 'name')
            subject_groups = SubjectGroup.objects.all().values('id', 'code', 'name', 'department_id')
            curricula = Curriculum.objects.all().values('id', 'code', 'name', 'academic_year', 'major_id')
            courses = Course.objects.all().values('id', 'code', 'name', 'curriculum_id')
            subject_types = SubjectType.objects.all().values('id', 'code', 'name')
            majors = Major.objects.all().values('id', 'code', 'name')
            
            # Lấy curriculum_id từ request nếu có
            curriculum_id = request.GET.get('curriculum_id')
            if curriculum_id:
                mon_hoc_data = self.get_subject_data(curriculum_id)
            else:
                mon_hoc_data = self.get_subject_data()
            
            context = {
                'departments': list(departments),
                'subject_groups': list(subject_groups),
                'curricula': list(curricula),
                'courses': list(courses),
                'subject_types': list(subject_types),
                'majors': list(majors),
                'mon_hoc_data': mon_hoc_data
            }
            return render(request, self.template_name, context)
        except Exception as e:
            print(f"Error in get: {str(e)}")
            # Fallback data nếu có lỗi
            context = {
                'departments': [],
                'subject_groups': [],
                'curricula': [],
                'courses': [],
                'subject_types': [],
                'majors': [],
                'mon_hoc_data': self.get_sample_data()
            }
            return render(request, self.template_name, context)
    
    def post(self, request):
        """Thêm chương trình đào tạo mới"""
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            try:
                data = json.loads(request.body)
                
                # Tạo curriculum mới
                curriculum = Curriculum.objects.create(
                    code=data.get('code'),
                    name=data.get('name'),
                    academic_year=data.get('academic_year'),
                    description=data.get('description'),
                    total_credits=data.get('total_credits', 0),
                    major_id=data.get('major_id'),
                    status='draft'
                )
                
                return JsonResponse({
                    'status': 'success', 
                    'message': 'Đã thêm chương trình đào tạo thành công',
                    'id': curriculum.id
                })
            except Exception as e:
                return JsonResponse({'status': 'error', 'message': str(e)})
        
        return JsonResponse({'status': 'error', 'message': 'Invalid request'})
    
    def put(self, request, id=None):
        """Cập nhật chương trình đào tạo"""
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            try:
                data = json.loads(request.body)
                
                if id:
                    # Cập nhật môn học cụ thể
                    subject = Subject.objects.get(id=id)
                    field = data.get('field')
                    value = data.get('value')
                    
                    if hasattr(subject, field):
                        setattr(subject, field, value)
                        subject.save()
                        
                    return JsonResponse({'status': 'success', 'message': 'Đã cập nhật môn học thành công'})
                else:
                    # Cập nhật thông tin chung của curriculum
                    curriculum_id = data.get('curriculum_id')
                    if curriculum_id:
                        curriculum = Curriculum.objects.get(id=curriculum_id)
                        curriculum.name = data.get('name', curriculum.name)
                        curriculum.academic_year = data.get('academic_year', curriculum.academic_year)
                        curriculum.description = data.get('description', curriculum.description)
                        curriculum.total_credits = data.get('total_credits', curriculum.total_credits)
                        curriculum.save()
                        
                    return JsonResponse({'status': 'success', 'message': 'Đã cập nhật chương trình thành công'})
                    
            except Exception as e:
                return JsonResponse({'status': 'error', 'message': str(e)})
        
        return JsonResponse({'status': 'error', 'message': 'Invalid request'})
    
    def get_subject_data(self, curriculum_id=None):
        """Lấy dữ liệu môn học từ database"""
        try:
            subjects = Subject.objects.select_related(
                'subject_type', 'department', 'subject_group', 'curriculum'
            )
            
            if curriculum_id:
                subjects = subjects.filter(curriculum_id=curriculum_id)
            
            subjects = subjects.order_by('subject_type__id', 'order_number')
            
            subject_data = []
            for subject in subjects:
                # Lấy phân bố học kỳ
                semester_allocations = SemesterAllocation.objects.filter(subject=subject)
                semester_data = {f'hk{alloc.semester}': float(alloc.credits) for alloc in semester_allocations}
                
                subject_data.append({
                    'id': subject.id,
                    'ma_mon_hoc': subject.code,
                    'ten_mon_hoc': subject.name,
                    'so_tin_chi': float(subject.credits),
                    'tong_so_gio': subject.total_hours,
                    'ly_thuyet': subject.theory_hours,
                    'thuc_hanh': subject.practice_hours,
                    'kiem_tra_thi': subject.exam_hours,
                    'hk1': semester_data.get('hk1', ''),
                    'hk2': semester_data.get('hk2', ''),
                    'hk3': semester_data.get('hk3', ''),
                    'hk4': semester_data.get('hk4', ''),
                    'hk5': semester_data.get('hk5', ''),
                    'hk6': semester_data.get('hk6', ''),
                    'don_vi': subject.department.name if subject.department else '',
                    'giang_vien': self.get_instructors_for_subject(subject),
                    'loai_mon': subject.subject_type.name if subject.subject_type else '',
                    'order_number': subject.order_number,
                    'curriculum_id': subject.curriculum_id,
                    'curriculum_name': subject.curriculum.name if subject.curriculum else ''
                })
            
            return subject_data
        except Exception as e:
            print(f"Error in get_subject_data: {str(e)}")
            return self.get_sample_data()
    
    def get_instructors_for_subject(self, subject):
        """Lấy danh sách giảng viên cho môn học"""
        # Triển khai logic lấy giảng viên từ TeachingAssignment
        return ""
    
    def get_sample_data(self):
        """Dữ liệu mẫu khi không kết nối được database"""
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
                'giang_vien': '',
                'loai_mon': 'Bắt buộc',
                'order_number': 1,
                'curriculum_id': 1,
                'curriculum_name': 'Chương trình mẫu'
            }
        ]

class ImportExcelView(View):
    def get(self, request):
        """Tải file Excel mẫu"""
        try:
            # Tạo DataFrame mẫu dựa trên file Excel đính kèm
            sample_data = {
                'TT': [1, 2, 3, 4, 5, 6],
                'Mã môn học': ['MH01', 'MH02', 'MH03', 'MH04', 'MH05', 'MH06'],
                'Tên học phần': [
                    'Giáo dục chính trị', 
                    'Pháp luật', 
                    'Giáo dục thể chất',
                    'GD Quốc phòng và An ninh',
                    'Tin học',
                    'Tiếng Anh'
                ],
                'Số tín chỉ': [4, 2, 2, 3, 3, 5],
                'Tổng số giờ': [75, 30, 60, 75, 75, 120],
                'Lý thuyết': [41, 18, 5, 36, 15, 42],
                'Thực hành': [29, 10, 51, 36, 58, 72],
                'Kiểm tra/Thi': [5, 2, 4, 3, 2, 6],
                'HK1': [4, '', '', '', 3, 5],
                'HK2': ['', '', 2, '', '', ''],
                'HK3': ['', '', '', 3, '', ''],
                'HK4': ['', 2, '', '', '', ''],
                'HK5': ['', '', '', '', '', ''],
                'HK6': ['', '', '', '', '', ''],
                'Đơn vị': [
                    'Khoa các BMC',
                    'Khoa các BMC', 
                    'Khoa các BMC',
                    'Khoa các BMC',
                    'Tổ Tin học',
                    'Khoa Ngoại ngữ'
                ],
                'Loại môn': [
                    'Bắt buộc', 'Bắt buộc', 'Bắt buộc', 
                    'Bắt buộc', 'Bắt buộc', 'Bắt buộc'
                ]
            }
            
            df = pd.DataFrame(sample_data)
            
            # Lưu file tạm
            file_path = os.path.join(settings.MEDIA_ROOT, 'mau_chuong_trinh_dao_tao.xlsx')
            df.to_excel(file_path, index=False, sheet_name='Chương trình đào tạo')
            
            # Trả về file để download
            with open(file_path, 'rb') as f:
                response = HttpResponse(f.read(), content_type='application/vnd.ms-excel')
                response['Content-Disposition'] = 'attachment; filename="mau_chuong_trinh_dao_tao.xlsx"'
            
            return response
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    def post(self, request):
        """Xử lý import file Excel"""
        try:
            if request.FILES.get('excel_file'):
                excel_file = request.FILES['excel_file']
                curriculum_id = request.POST.get('curriculum_id')
                
                if not curriculum_id:
                    return JsonResponse({'status': 'error', 'message': 'Vui lòng chọn chương trình đào tạo'})
                
                # Đọc file Excel
                df = pd.read_excel(excel_file)
                
                # Xử lý dữ liệu và lưu vào database
                result = self.process_excel_data(df, curriculum_id, request.user)
                
                if result['status'] == 'success':
                    return JsonResponse({
                        'status': 'success', 
                        'message': f'Import file Excel thành công: {result["created_count"]} môn học được tạo, {result["updated_count"]} môn học được cập nhật',
                        'data': result['processed_data']
                    })
                else:
                    return JsonResponse({'status': 'error', 'message': result['message']})
                    
            else:
                return JsonResponse({'status': 'error', 'message': 'Không tìm thấy file'})
                
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Lỗi khi xử lý file: {str(e)}'})
    
    def process_excel_data(self, df, curriculum_id, user):
        """Xử lý dữ liệu từ Excel và lưu vào database"""
        try:
            curriculum = Curriculum.objects.get(id=curriculum_id)
            created_count = 0
            updated_count = 0
            processed_data = []
            errors = []
            
            for index, row in df.iterrows():
                try:
                    # Bỏ qua các dòng trống hoặc dòng tiêu đề
                    if pd.isna(row.get('Mã môn học')) or row.get('Mã môn học') == 'Mã môn học':
                        continue
                    
                    # Lấy hoặc tạo department
                    department_name = row.get('Đơn vị', '').strip()
                    department = None
                    if department_name:
                        department, _ = Department.objects.get_or_create(
                            name=department_name,
                            defaults={'code': department_name[:10], 'name': department_name}
                        )
                    
                    # Lấy hoặc tạo subject_type
                    subject_type_name = row.get('Loại môn', 'Bắt buộc').strip()
                    subject_type, _ = SubjectType.objects.get_or_create(
                        name=subject_type_name,
                        defaults={'code': subject_type_name[:10], 'name': subject_type_name}
                    )
                    
                    # Tạo hoặc cập nhật subject
                    subject, created = Subject.objects.update_or_create(
                        curriculum=curriculum,
                        code=row.get('Mã môn học'),
                        defaults={
                            'name': row.get('Tên học phần'),
                            'credits': float(row.get('Số tín chỉ', 0)),
                            'total_hours': int(row.get('Tổng số giờ', 0)),
                            'theory_hours': int(row.get('Lý thuyết', 0)),
                            'practice_hours': int(row.get('Thực hành', 0)),
                            'exam_hours': int(row.get('Kiểm tra/Thi', 0)),
                            'department': department,
                            'subject_type': subject_type,
                            'order_number': int(row.get('TT', index + 1))
                        }
                    )
                    
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
                    
                    # Xử lý phân bố học kỳ
                    for hk in range(1, 7):
                        credits = row.get(f'HK{hk}')
                        if credits and str(credits).strip() and str(credits).strip() != 'nan':
                            try:
                                credit_value = float(credits)
                                SemesterAllocation.objects.update_or_create(
                                    subject=subject,
                                    semester=hk,
                                    defaults={'credits': credit_value}
                                )
                            except (ValueError, TypeError):
                                pass
                    
                    processed_data.append({
                        'ma_mon_hoc': subject.code,
                        'ten_mon_hoc': subject.name,
                        'so_tin_chi': float(subject.credits),
                        'tong_so_gio': subject.total_hours,
                    })
                    
                except Exception as e:
                    errors.append(f"Dòng {index + 2}: {str(e)}")
            
            # Lưu lịch sử import
            ImportHistory.objects.create(
                curriculum=curriculum,
                file_name=user.username if user else 'Unknown',
                imported_by=user,
                record_count=len(processed_data),
                status='success' if not errors else 'partial',
                errors=errors if errors else None
            )
            
            return {
                'status': 'success',
                'created_count': created_count,
                'updated_count': updated_count,
                'processed_data': processed_data,
                'errors': errors
            }
            
        except Exception as e:
            return {'status': 'error', 'message': str(e)}

class ThongKeView(View):
    def get(self, request):
        """API trả về thống kê"""
        try:
            curriculum_id = request.GET.get('curriculum_id')
            
            if curriculum_id:
                subjects = Subject.objects.filter(curriculum_id=curriculum_id)
            else:
                subjects = Subject.objects.all()
            
            total_credits = sum(float(subject.credits) for subject in subjects)
            total_hours = sum(subject.total_hours for subject in subjects)
            total_theory = sum(subject.theory_hours for subject in subjects)
            total_practice = sum(subject.practice_hours for subject in subjects)
            
            ty_le_ly_thuyet = (total_theory / total_hours * 100) if total_hours > 0 else 0
            ty_le_thuc_hanh = (total_practice / total_hours * 100) if total_hours > 0 else 0
            
            thong_ke = {
                'tong_tin_chi': total_credits,
                'tong_gio': total_hours,
                'ty_le_ly_thuyet': f'{ty_le_ly_thuyet:.1f}%',
                'ty_le_thuc_hanh': f'{ty_le_thuc_hanh:.1f}%'
            }
            return JsonResponse(thong_ke)
        except Exception as e:
            # Trả về dữ liệu mẫu nếu có lỗi
            return JsonResponse({
                'tong_tin_chi': 76.0,
                'tong_gio': 2475.0,
                'ty_le_ly_thuyet': '30.5%',
                'ty_le_thuc_hanh': '69.5%'
            })

# API endpoints cho các dropdown
@csrf_exempt
def api_departments(request):
    """API lấy danh sách khoa"""
    departments = Department.objects.all().values('id', 'code', 'name')
    return JsonResponse(list(departments), safe=False)

@csrf_exempt
def api_subject_groups(request):
    """API lấy danh sách tổ bộ môn theo khoa"""
    department_id = request.GET.get('department_id')
    if department_id:
        subject_groups = SubjectGroup.objects.filter(department_id=department_id).values('id', 'code', 'name')
    else:
        subject_groups = SubjectGroup.objects.all().values('id', 'code', 'name')
    return JsonResponse(list(subject_groups), safe=False)

@csrf_exempt
def api_curricula(request):
    """API lấy danh sách chương trình đào tạo"""
    curricula = Curriculum.objects.all().values('id', 'code', 'name', 'academic_year')
    return JsonResponse(list(curricula), safe=False)

@csrf_exempt
def api_courses(request):
    """API lấy danh sách khóa học theo chương trình đào tạo"""
    curriculum_id = request.GET.get('curriculum_id')
    if curriculum_id:
        courses = Course.objects.filter(curriculum_id=curriculum_id).values('id', 'code', 'name')
    else:
        courses = Course.objects.all().values('id', 'code', 'name')
    return JsonResponse(list(courses), safe=False)

@csrf_exempt
def api_subjects(request):
    """API lấy danh sách môn học theo bộ lọc"""
    curriculum_id = request.GET.get('curriculum_id')
    department_id = request.GET.get('department_id')
    subject_group_id = request.GET.get('subject_group_id')
    course_id = request.GET.get('course_id')
    
    subjects = Subject.objects.select_related('subject_type', 'department', 'curriculum').all()
    
    if curriculum_id:
        subjects = subjects.filter(curriculum_id=curriculum_id)
    if department_id:
        subjects = subjects.filter(department_id=department_id)
    if subject_group_id:
        subjects = subjects.filter(subject_group_id=subject_group_id)
    
    # Sắp xếp theo loại môn và thứ tự
    subjects = subjects.order_by('subject_type__id', 'order_number')
    
    subject_data = []
    for subject in subjects:
        semester_allocations = SemesterAllocation.objects.filter(subject=subject)
        semester_data = {f'hk{alloc.semester}': float(alloc.credits) for alloc in semester_allocations}
        
        subject_data.append({
            'id': subject.id,
            'ma_mon_hoc': subject.code,
            'ten_mon_hoc': subject.name,
            'so_tin_chi': float(subject.credits),
            'tong_so_gio': subject.total_hours,
            'ly_thuyet': subject.theory_hours,
            'thuc_hanh': subject.practice_hours,
            'kiem_tra_thi': subject.exam_hours,
            'hk1': semester_data.get('hk1', ''),
            'hk2': semester_data.get('hk2', ''),
            'hk3': semester_data.get('hk3', ''),
            'hk4': semester_data.get('hk4', ''),
            'hk5': semester_data.get('hk5', ''),
            'hk6': semester_data.get('hk6', ''),
            'don_vi': subject.department.name if subject.department else '',
            'giang_vien': '',
            'loai_mon': subject.subject_type.name if subject.subject_type else '',
            'curriculum_id': subject.curriculum_id,
            'curriculum_name': subject.curriculum.name if subject.curriculum else ''
        })
    
    return JsonResponse(subject_data, safe=False)

@csrf_exempt
def api_subject_types(request):
    """API lấy danh sách loại môn học"""
    subject_types = SubjectType.objects.all().values('id', 'code', 'name')
    return JsonResponse(list(subject_types), safe=False)

@csrf_exempt
def api_majors(request):
    """API lấy danh sách ngành đào tạo"""
    majors = Major.objects.all().values('id', 'code', 'name')
    return JsonResponse(list(majors), safe=False)

@csrf_exempt
def create_curriculum(request):
    """API tạo chương trình đào tạo mới"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            curriculum = Curriculum.objects.create(
                code=data.get('code'),
                name=data.get('name'),
                academic_year=data.get('academic_year'),
                description=data.get('description'),
                major_id=data.get('major_id'),
                total_credits=data.get('total_credits', 0),
                status='draft'
            )
            return JsonResponse({
                'status': 'success',
                'message': 'Đã tạo chương trình đào tạo thành công',
                'id': curriculum.id
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'})