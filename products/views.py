from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Sum, F, Q, Case, When, IntegerField
from django.views.decorators.csrf import csrf_exempt
import json
from django.shortcuts import render, get_object_or_404
from django.core.serializers import serialize
from django.views import View
from .models import (
    Department, SubjectGroup, Curriculum, Course, Subject, SubjectType, 
    SemesterAllocation, Major, ImportHistory, Class, CombinedClass, TeachingAssignment, Instructor
)
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
            curriculum_id = request.GET.get('chuong-trinh-dao-tao')
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
                # 'mon_hoc_data': json.dumps(mon_hoc_data, default=str)  # Serialize với default=str
            }
            
            return render(request, self.template_name, context)
        except Exception as e:
            print(f"Error in get: {str(e)}")
            # Fallback data nếu có lỗi
            context = {
                'departments': [],
                'subject_groups': [],
                'curriculum': [],
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
                    curriculum_subject = Subject.objects.get(id=id)
                    field = data.get('field')
                    value = data.get('value')
                                        
                    # Xử lý các trường học kỳ (HK1-HK6)
                    if field and field.startswith('hk'):
                        semester = int(field.replace('hk', ''))
                        
                        # Xử lý giá trị học kỳ
                        if value == '' or value is None:
                            # Xóa phân bố học kỳ nếu tồn tại
                            SemesterAllocation.objects.filter(
                                base_subject=curriculum_subject, 
                                semester=semester
                            ).delete()
                        else:
                            # Cập nhật hoặc tạo mới phân bố học kỳ
                            try:
                                credits_value = float(value)
                                SemesterAllocation.objects.update_or_create(
                                    base_subject=curriculum_subject,
                                    semester=semester,
                                    defaults={'credits': credits_value}
                                )
                            except (ValueError, TypeError):
                                return JsonResponse({
                                    'status': 'error', 
                                    'message': f'Giá trị tín chỉ không hợp lệ: {value}'
                                })
                        
                        return JsonResponse({
                            'status': 'success', 
                            'message': f'Đã cập nhật phân bố học kỳ HK{semester}'
                        })
                    
                    # Xử lý trường department (quan hệ)
                    elif field == 'department':
                        # Tìm hoặc tạo department mới
                        if value and value.strip():
                            department, created = Department.objects.get_or_create(
                                name=value.strip(),
                                defaults={'code': value.strip()[:10].upper().replace(' ', '')}
                            )
                            curriculum_subject.department = department
                            curriculum_subject.save()
                        else:
                            curriculum_subject.department = None
                            curriculum_subject.save()
                        return JsonResponse({
                            'status': 'success', 
                            'message': 'Đã cập nhật đơn vị quản lý'
                        })
                    
                    # Bỏ qua trường instructor vì không tồn tại trong model
                    elif field == 'instructor':
                        return JsonResponse({
                            'status': 'success', 
                            'message': 'Trường giảng viên được bỏ qua (chưa được triển khai)'
                        })
                    
                    # Xử lý các trường khác của Subject
                    elif hasattr(curriculum_subject, field):
                        # Xử lý kiểu dữ liệu
                        if field in ['credits']:
                            try:
                                value = float(value) if value else 0
                            except (ValueError, TypeError):
                                return JsonResponse({
                                    'status': 'error', 
                                    'message': f'Giá trị {field} không hợp lệ: {value}'
                                })
                        elif field in ['total_hours', 'theory_hours', 'practice_hours', 'exam_hours', 'order_number', 'semester']:
                            try:
                                value = int(value) if value else 0
                            except (ValueError, TypeError):
                                return JsonResponse({
                                    'status': 'error', 
                                    'message': f'Giá trị {field} không hợp lệ: {value}'
                                })
                        
                        setattr(curriculum_subject, field, value)
                        curriculum_subject.save()
                        
                        return JsonResponse({
                            'status': 'success', 
                            'message': f'Đã cập nhật {field} thành công'
                        })
                    else:
                        return JsonResponse({
                            'status': 'error', 
                            'message': f'Trường {field} không tồn tại'
                        })
                        
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
                        
                    return JsonResponse({
                        'status': 'success', 
                        'message': 'Đã cập nhật chương trình thành công'
                    })
                    
            except Subject.DoesNotExist:
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Môn học không tồn tại'
                })
            except Curriculum.DoesNotExist:
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Chương trình đào tạo không tồn tại'
                })
            except Exception as e:
                print(f"Error in PUT: {str(e)}")  # Debug log
                return JsonResponse({
                    'status': 'error', 
                    'message': f'Lỗi khi cập nhật: {str(e)}'
                })
        
        return JsonResponse({
            'status': 'error', 
            'message': 'Invalid request'
        })
    
    def delete(self, request, id=None):
        """Xóa môn học"""
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            try:
                if id:
                    curriculum_subject = Subject.objects.get(id=id)
                    subject_name = curriculum_subject.name
                    curriculum_subject.delete()
                    
                    return JsonResponse({
                        'status': 'success', 
                        'message': f'Đã xóa môn học {subject_name}'
                    })
                else:
                    return JsonResponse({
                        'status': 'error', 
                        'message': 'Thiếu ID môn học'
                    })
                    
            except Subject.DoesNotExist:
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Môn học trong Chươgn trình không tồn tại'
                })
            except Exception as e:
                return JsonResponse({
                    'status': 'error', 
                    'message': f'Lỗi khi xóa: {str(e)}'
                })
        
        return JsonResponse({
            'status': 'error', 
            'message': 'Invalid request'
        })
        
    def get_subject_data(self, curriculum_id=None):
        """Lấy dữ liệu môn học từ database"""
        try:           
            if curriculum_id:
                curriculum_subjects = Subject.objects.select_related('subject_type', 'department', 'subject_group', 'curriculum'
                ).filter(curriculum=curriculum_id)
            else:
                # Lấy tất cả CurriculumSubject
                curriculum_subjects = Subject.objects.select_related(
                    'subject_type', 'department', 'subject_group', 'curriculum'
                ).all()
                
            curriculum_subjects = curriculum_subjects.order_by('order_number')
            
            subject_data = []
            for cs in curriculum_subjects:
                # Lấy phân bố học kỳ
                semester_allocations = SemesterAllocation.objects.filter(base_subject=cs)
                semester_data = {f'hk{alloc.semester}': float(alloc.credits) for alloc in semester_allocations}
                
                subject_data.append({
                    'id': cs.id,
                    'ma_mon_hoc': cs.code,
                    'ten_mon_hoc': cs.name,
                    'curriculum_id': cs.curriculum.id if cs.curriculum else None,
                    'curriculum_code': cs.curriculum.code if cs.curriculum else '',
                    'curriculum_academic_year': cs.curriculum.academic_year if cs.curriculum else '',
                    'loai_mon': cs.subject_type.name if cs.subject_type else '',
                    'so_tin_chi': float(cs.credits),
                    'tong_so_gio': cs.total_hours,
                    'ly_thuyet': cs.theory_hours,
                    'thuc_hanh': cs.practice_hours,
                    'kiem_tra_thi': cs.exam_hours,
                    'hk1': semester_data.get('hk1', ''),
                    'hk2': semester_data.get('hk2', ''),
                    'hk3': semester_data.get('hk3', ''),
                    'hk4': semester_data.get('hk4', ''),
                    'hk5': semester_data.get('hk5', ''),
                    'hk6': semester_data.get('hk6', ''),
                    'don_vi': cs.department.name if cs.department else '',
                    'bo_mon': cs.subject_group.name if cs.subject_group else '',
                    'giang_vien': self.get_instructors_for_subject(cs),
                    'order_number': cs.order_number,
                    'original_code': cs.original_code if cs.original_code else '',
                    'subject_id': cs.id
                })
            
            return subject_data
        except Exception as e:
            return self.get_sample_data()
    
    def get_instructors_for_subject(self, curriculum_subject):
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
                'curriculum_name': 'Chương trình mẫu',
                'subject_id': 1
            }
        ]

import io
from django.http import HttpResponse
from django.core.files.base import ContentFile

class ImportExcelView(View):
    def get(self, request):
        """Tải file Excel mẫu"""
        try:
            sample_data = {
                'TT': [1, 2, 3, 4, 5, 6, 7, 8],
                'Mã môn học': ['MH01', 'MH02', 'MH03', 'MH04', 'MH05', 'MH06', 'MH07', 'MH08'],
                'Tên học phần': [
                    'Giáo dục chính trị', 
                    'Pháp luật', 
                    'Giáo dục thể chất',
                    'GD Quốc phòng và An ninh',
                    'Tin học',
                    'Tiếng Anh',
                    'GD kỹ năng mềm',
                    'Tài chính doanh nghiệp'
                ],
                'Số tín chỉ': [4, 2, 2, 3, 3, 5, 3, 2],
                'Tổng số giờ': [75, 30, 60, 75, 75, 120, 75, 30],
                'Lý thuyết': [41, 18, 5, 36, 15, 42, 15, 28],
                'Thực hành': [29, 10, 51, 36, 58, 72, 58, 0],
                'Kiểm tra/Thi': [5, 2, 4, 3, 2, 6, 2, 2],
                'HK1': [4, '', '', '', 3, 5, '', ''],
                'HK2': ['', '', 2, '', '', '', 3, ''],
                'HK3': ['', '', '', 3, '', '', '', ''],
                'HK4': ['', 2, '', '', '', '', '', 2],
                'HK5': ['', '', '', '', '', '', '', ''],
                'HK6': ['', '', '', '', '', '', '', ''],
                'Đơn vị': [
                    'Khoa Khoa học cơ bản',
                    'Khoa Khoa học cơ bản', 
                    'Khoa Khoa học cơ bản',
                    'Khoa Khoa học cơ bản',
                    'Khoa Điện - Công nghệ Thông tin',
                    'Khoa Ngoại ngữ',
                    'Khoa Khoa học cơ bản',
                    'Khoa Kinh tế - Nông, Lâm nghiệp'
                ],
                'Loại môn': [
                    'Bắt buộc', 'Bắt buộc', 'Bắt buộc', 
                    'Bắt buộc', 'Bắt buộc', 'Bắt buộc',
                    'Bắt buộc', 'Bắt buộc'
                ],
                'Tổ bộ môn': [
                    'BM Lý luận chính trị', 'BM Lý luận chính trị', 'BM GD Thể chất & GD Quốc phòng và An ninh',
                    'BM GD Thể chất & GD Quốc phòng và An ninh', 'BM Công nghệ thông tin', 'BM Tiếng Anh', 
                    'BM Tâm lý học và Giáo dục học', 'BM Kinh tế'
                ],
                'Điều kiện tiên quyết': ['', '', '', '', '', '', '', ''],
                'Chuẩn đầu ra': ['', '', '', '', '', '', '', ''],
                'Mô tả môn học': ['', '', '', '', '', '', '', ''],
            }
            
            df = pd.DataFrame(sample_data)
            
            # Lấy dữ liệu từ database cho sheet hướng dẫn
            departments = Department.objects.all().values('name')
            subject_types = SubjectType.objects.all().values('name')
            
            # Tạo DataFrame cho các giá trị có sẵn
            df_departments = pd.DataFrame(list(departments))
            df_subject_types = pd.DataFrame(list(subject_types))
            
            # Tạo file trong memory
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Sheet chính với dữ liệu mẫu
                df.to_excel(writer, index=False, sheet_name='Chương trình đào tạo')
                
                # Sheet hướng dẫn với các giá trị có sẵn
                df_departments.to_excel(writer, index=False, sheet_name='Hướng dẫn', startrow=1)
                df_subject_types.to_excel(writer, index=False, sheet_name='Hướng dẫn', startrow=len(df_departments) + 4)
                
                # Lấy worksheet để thêm tiêu đề
                worksheet = writer.sheets['Hướng dẫn']
                worksheet.cell(1, 1, "DANH SÁCH ĐƠN VỊ CÓ SẴN")
                worksheet.cell(len(df_departments) + 4, 1, "DANH SÁCH LOẠI MÔN CÓ SẴN")
                
                # Thêm ghi chú
                worksheet.cell(len(df_departments) + len(df_subject_types) + 7, 1, 
                              "LƯU Ý: Khi nhập dữ liệu, vui lòng sử dụng các giá trị từ danh sách trên để đảm bảo tính nhất quán.")
            
            output.seek(0)
            
            # Trả về file để download
            response = HttpResponse(
                output.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = 'attachment; filename="mau_chuong_trinh_dao_tao.xlsx"'
            response['Content-Length'] = len(output.getvalue())
            
            return response
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f"Lỗi tạo file mẫu {str(e)}"})
    
    def post(self, request):
        """Xử lý import file Excel"""
        try:
            if request.FILES.get('excel_file'):
                excel_file = request.FILES['excel_file']
                curriculum_id = request.POST.get('curriculum_id')
                sheet_name = request.POST.get('sheet_name', '')  # Lấy tên sheet từ request
                
                if not curriculum_id:
                    return JsonResponse({'status': 'error', 'message': 'Vui lòng chọn chương trình đào tạo'})
                
                # Kiểm tra định dạng file
                if not excel_file.name.endswith(('.xlsx', '.xls')):
                    return JsonResponse({'status': 'error', 'message': 'File phải có định dạng Excel (.xlsx hoặc .xls)'})
                
                # Kiểm tra kích thước file (tối đa 10MB)
                if excel_file.size > 10 * 1024 * 1024:
                    return JsonResponse({'status': 'error', 'message': 'File không được vượt quá 10MB'})
                
                try:
                    # Đọc file Excel để lấy danh sách sheet
                    excel_file.seek(0)  # Reset file pointer
                    xls = pd.ExcelFile(excel_file)
                    sheet_names = xls.sheet_names
                    
                    # Nếu không có sheet_name được chọn, sử dụng sheet đầu tiên
                    if not sheet_name and sheet_names:
                        sheet_name = sheet_names[0]
                        
                    # Đọc file Excel cụ thể
                    df = pd.read_excel(excel_file, sheet_name=sheet_name)
                    
                except Exception as e:
                    return JsonResponse({'status': 'error', 'message': f'Không thể đọc file Excel: {str(e)}'})
                
                # Xử lý dữ liệu và lưu vào database - TRUYỀN excel_file VÀO
                result = self.process_excel_data(df, curriculum_id, request.user, excel_file, sheet_name)
                
                if result['status'] == 'success':
                    return JsonResponse({
                        'status': 'success', 
                        'message': f'Import file Excel thành công: {result["created_count"]} môn học được tạo, {result["updated_count"]} môn học được cập nhật',
                        'data': result['processed_data'],
                        'sheet_used': sheet_name,
                        'code_mapping': [{'original': item['ma_mon_hoc_goc'], 'new': item['ma_mon_hoc_moi']} 
                                    for item in result['processed_data']]
                    })
                else:
                    return JsonResponse({'status': 'error', 'message': result['message']})
                    
            else:
                return JsonResponse({'status': 'error', 'message': 'Không tìm thấy file'})
                
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Lỗi khi xử lý file: {str(e)}'})
    
    def process_excel_data(self, df, curriculum_id, user, excel_file, sheet_name):  # THÊM excel_file, sheet_name VÀO THAM SỐ
        """Xử lý dữ liệu từ Excel và lưu vào database"""
        try:
            curriculum = Curriculum.objects.get(id=curriculum_id)
            created_count = 0
            updated_count = 0
            processed_data = []
            errors = []
            
            # Kiểm tra cấu trúc file
            required_columns = ['Mã môn học', 'Tên học phần', 'Số tín chỉ']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return {
                    'status': 'error', 
                    'message': f'File thiếu các cột bắt buộc: {", ".join(missing_columns)}'
                }
            
            for index, row in df.iterrows():
                try:
                    # Bỏ qua các dòng trống hoặc dòng tiêu đề
                    if pd.isna(row.get('Mã môn học')) or str(row.get('Mã môn học')).strip() in ['', 'Mã môn học', 'nan']:
                        continue
                    
                    # Chuẩn hóa dữ liệu
                    original_code = str(row.get('Mã môn học')).strip()
                    ten_mon_hoc = str(row.get('Tên học phần')).strip()
                    
                    if not original_code or not ten_mon_hoc:
                        errors.append(f"Dòng {index + 2}: Mã môn học và Tên học phần không được để trống")
                        continue
                    
                    # Xử lý số tín chỉ
                    try:
                        so_tin_chi = float(row.get('Số tín chỉ', 0))
                    except (ValueError, TypeError):
                        so_tin_chi = 0
                    
                    # Xử lý số giờ
                    try:
                        tong_so_gio = int(float(row.get('Tổng số giờ', 0)))
                    except (ValueError, TypeError):
                        tong_so_gio = 0
                    
                    try:
                        ly_thuyet = int(float(row.get('Lý thuyết', 0)))
                    except (ValueError, TypeError):
                        ly_thuyet = 0
                    
                    try:
                        thuc_hanh = int(float(row.get('Thực hành', 0)))
                    except (ValueError, TypeError):
                        thuc_hanh = 0
                    
                    try:
                        kiem_tra_thi = int(float(row.get('Kiểm tra/Thi', 0)))
                    except (ValueError, TypeError):
                        kiem_tra_thi = 0
                    
                    # Xác định học kỳ mặc định từ phân bố học kỳ
                    default_semester = None
                    for hk in range(1, 7):
                        column_name = f'HK{hk}'
                        if column_name in df.columns:
                            credits_value = row.get(column_name)
                            if credits_value and str(credits_value).strip() and str(credits_value).strip() not in ['', 'nan', 'x', 'X']:
                                default_semester = hk
                                break
                    
                    # Lấy hoặc tạo department - sử dụng giá trị chính xác từ database
                    department_name = str(row.get('Đơn vị', '')).strip()
                    department = None
                    if department_name and department_name not in ['', 'nan']:
                        try:
                            # Tìm department theo tên chính xác
                            department = Department.objects.get(name=department_name)
                        except Department.DoesNotExist:
                            department, _ = Department.objects.get_or_create(
                                name=department_name,
                                defaults={
                                    'code': department_name[:10].upper().replace(' ', ''),
                                    'name': department_name
                                }
                            )
                            errors.append(f"Dòng {index + 2}: Đã tạo mới đơn vị '{department_name}'")
                    
                    # Lấy hoặc tạo subject_type - sử dụng giá trị chính xác từ database
                    subject_type_name = str(row.get('Loại môn', 'Bắt buộc')).strip()
                    if not subject_type_name or subject_type_name == 'nan':
                        subject_type_name = 'Bắt buộc'
                    
                    try:
                        subject_type = SubjectType.objects.get(name=subject_type_name)
                    except SubjectType.DoesNotExist:
                        subject_type, _ = SubjectType.objects.get_or_create(
                            name=subject_type_name,
                            defaults={
                                'code': subject_type_name[:10].upper().replace(' ', ''),
                                'name': subject_type_name
                            }
                        )
                        errors.append(f"Dòng {index + 2}: Đã tạo mới loại môn '{subject_type_name}'")
                    
                    # Lấy hoặc tạo subject_group nếu có
                    subject_group = None
                    subject_group_name = str(row.get('Tổ bộ môn', '')).strip()
                    if subject_group_name and subject_group_name not in ['', 'nan']:
                        subject_group, _ = SubjectGroup.objects.get_or_create(
                            department=department,
                            name=subject_group_name,
                            defaults={
                                'code': subject_group_name[:10].upper().replace(' ', ''),
                                'name': subject_group_name,
                                'department': department
                            }
                        )
                    
                    # Xử lý thứ tự
                    try:
                        order_number = int(row.get('TT', index + 1))
                    except (ValueError, TypeError):
                        order_number = index + 1
                    
                    # Tạo mã duy nhất cho môn học
                    curriculum_prefix = curriculum.code.replace(' ', '_').upper()[:10]
                    base_code = original_code
                    
                    # Kiểm tra xem mã đã tồn tại chưa
                    proposed_code = f"{curriculum_prefix}_{base_code}"
                    counter = 1
                    unique_code = proposed_code
                    
                    while Subject.objects.filter(code=unique_code).exists():
                        # Kiểm tra xem có phải là cùng một môn học không (dựa trên tên và các thuộc tính)
                        existing_subject = Subject.objects.get(code=unique_code)
                        if (existing_subject.name == ten_mon_hoc and
                            existing_subject.curriculum.id == curriculum_id and
                            float(existing_subject.credits) == so_tin_chi and
                            int(existing_subject.semester) == default_semester):
                            # Nếu giống hệt, sử dụng môn học hiện có
                            break
                        else:
                            # Nếu khác, tạo mã mới
                            unique_code = f"{proposed_code}_{counter}"
                            counter += 1
                    
                    # Tạo hoặc cập nhật subject
                    is_elective = False
                    if subject_type_name == "Môn học tự chọn":
                        is_elective = True                        
                        
                    subject, created = Subject.objects.update_or_create(
                        curriculum = curriculum, 
                        code = unique_code,
                        defaults={
                            'name': ten_mon_hoc,
                            'credits': so_tin_chi,
                            'semester': default_semester,
                            'total_hours': tong_so_gio,
                            'theory_hours': ly_thuyet,
                            'practice_hours': thuc_hanh,
                            'exam_hours': kiem_tra_thi,
                            'department': department,
                            'subject_type': subject_type,
                            'subject_group': subject_group,
                            'is_elective': is_elective,
                            'order_number': order_number,
                            'original_code': original_code
                        }
                    )
                    
                    # # Tạo hoặc cập nhật CurriculumSubject
                    # curriculum_subject, cs_created = CurriculumSubject.objects.update_or_create(
                    #     curriculum=curriculum,
                    #     subject=base_subject,
                    #     defaults={
                    #         'credits': so_tin_chi,
                    #         'total_hours': tong_so_gio,
                    #         'theory_hours': ly_thuyet,
                    #         'practice_hours': thuc_hanh,
                    #         'exam_hours': kiem_tra_thi,
                    #         'order_number': order_number,
                    #         'semester': default_semester
                    #     }
                    # )
                    
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
                    
                    # Xử lý phân bố học kỳ
                    for hk in range(1, 7):
                        column_name = f'HK{hk}'
                        if column_name in df.columns:
                            credits_value = row.get(column_name)
                            if credits_value and str(credits_value).strip() and str(credits_value).strip() not in ['', 'nan', 'x', 'X']:
                                try:
                                    credit_value = float(credits_value)
                                    SemesterAllocation.objects.update_or_create(
                                        base_subject=subject,
                                        semester=hk,
                                        defaults={'credits': credit_value}
                                    )
                                except (ValueError, TypeError) as e:
                                    errors.append(f"Dòng {index + 2} - HK{hk}: Giá trị tín chỉ không hợp lệ: {credits_value}")
                    
                    processed_data.append({
                        'ma_mon_hoc_goc': original_code,
                        'ma_mon_hoc_moi': subject.code,
                        'ten_mon_hoc': subject.name,
                        'so_tin_chi': float(subject.credits),
                        'tong_so_gio': subject.total_hours,
                        'ly_thuyet': subject.theory_hours,
                        'thuc_hanh': subject.practice_hours,
                        'kiem_tra_thi': subject.exam_hours,
                        'hoc_ky': subject.semester
                    })
                    
                except Exception as e:
                    error_msg = f"Dòng {index + 2}: {str(e)}"
                    errors.append(error_msg)
            
            # Lưu lịch sử import - SỬ DỤNG excel_file ĐÃ ĐƯỢC TRUYỀN VÀO
            # ImportHistory.objects.create(
            #     curriculum=curriculum,
            #     file_name=excel_file.name,  # BÂY GIỜ excel_file ĐÃ ĐƯỢC XÁC ĐỊNH
            #     file_size=excel_file.size,   # BÂY GIỜ excel_file ĐÃ ĐƯỢC XÁC ĐỊNH
            #     imported_by=user,
            #     record_count=len(processed_data),
            #     status='success' if not errors else 'partial',
            #     errors=errors if errors else None,
            #     additional_info=f"Sheet được sử dụng: {sheet_name}"
            # )
            
            import_history_data = {
                'curriculum': curriculum,
                'file_name': excel_file.name,
                'file_size': excel_file.size,
                'imported_by': user,
                'record_count': len(processed_data),
                'status': 'success' if not errors else 'partial',
                'errors': errors if errors else None,
            }
            
            # Chỉ thêm additional_info nếu không gây lỗi
            try:
                # Kiểm tra xem model có trường này không
                test_instance = ImportHistory()
                if hasattr(test_instance, 'additional_info'):
                    import_history_data['additional_info'] = f"Sheet được sử dụng: {sheet_name}"
            except:
                pass  # Bỏ qua nếu có lỗi
            
            ImportHistory.objects.create(**import_history_data)
                        
            return {
                'status': 'success',
                'created_count': created_count,
                'updated_count': updated_count,
                'processed_data': processed_data,
                'errors': errors
            }
            
        except Curriculum.DoesNotExist:
            return {'status': 'error', 'message': 'Chương trình đào tạo không tồn tại'}
        except Exception as e:
            return {'status': 'error', 'message': f'Lỗi xử lý dữ liệu: {str(e)}'}
    
    def get_sheet_names(self, excel_file):
        """Lấy danh sách các sheet trong file Excel"""
        try:
            excel_file.seek(0)  # Reset file pointer
            xls = pd.ExcelFile(excel_file)
            return xls.sheet_names
        except Exception as e:
            print(f"Error getting sheet names: {str(e)}")
            return []

# Hàm tạo mã duy nhất (helper)
def generate_subject_code(self, curriculum, original_code, name, credits, total_hours):
    """Tạo mã môn học duy nhất"""
    curriculum_prefix = curriculum.code.replace(' ', '_').upper()[:10]
    base_code = original_code
    
    # Tạo mã đề xuất
    proposed_code = f"{curriculum_prefix}_{base_code}"
    
    # Kiểm tra xem mã đã tồn tại chưa
    counter = 1
    unique_code = proposed_code
    
    while Subject.objects.filter(code=unique_code).exists():
        existing_subject = Subject.objects.get(code=unique_code)
        
        # Kiểm tra xem có phải cùng một môn học không
        is_same_subject = (
            existing_subject.name == name and
            float(existing_subject.credits) == credits and
            existing_subject.total_hours == total_hours
        )
        
        if is_same_subject:
            # Nếu là cùng môn học, sử dụng mã hiện tại
            break
        else:
            # Nếu khác môn học, tạo mã mới
            unique_code = f"{proposed_code}_{counter}"
            counter += 1
    
    return unique_code
    
class ThongKeView(View):
    def get(self, request):
        """API trả về thống kê"""
        try:
            curriculum_id = request.GET.get('curriculum_id')
            
            if curriculum_id:
                # Tính tổng từ CurriculumSubject
                curriculum_subjects = Subject.objects.filter(curriculum_id=curriculum_id)
                total_credits = sum(float(cs.credits) for cs in curriculum_subjects)
                total_hours = sum(cs.total_hours for cs in curriculum_subjects)
                total_theory = sum(cs.theory_hours for cs in curriculum_subjects)
                total_practice = sum(cs.practice_hours for cs in curriculum_subjects)
            else:
                # Tính tổng từ tất cả CurriculumSubject
                curriculum_subjects = Subject.objects.all()
                total_credits = sum(float(cs.credits) for cs in curriculum_subjects)
                total_hours = sum(cs.total_hours for cs in curriculum_subjects)
                total_theory = sum(cs.theory_hours for cs in curriculum_subjects)
                total_practice = sum(cs.practice_hours for cs in curriculum_subjects)
            
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
def api_get_sheet_names(request):
    """API lấy danh sách sheet từ file Excel"""
    if request.method == 'POST' and request.FILES.get('excel_file'):
        try:
            excel_file = request.FILES['excel_file']
            
            # Kiểm tra định dạng file
            if not excel_file.name.endswith(('.xlsx', '.xls')):
                return JsonResponse({'status': 'error', 'message': 'File phải có định dạng Excel'})
            
            # Lấy danh sách sheet
            sheet_names = []
            try:
                excel_file.seek(0)  # Reset file pointer
                xls = pd.ExcelFile(excel_file)
                sheet_names = xls.sheet_names
            except Exception as e:
                return JsonResponse({'status': 'error', 'message': f'Không thể đọc file Excel: {str(e)}'})
            
            return JsonResponse({
                'status': 'success',
                'sheet_names': sheet_names
            })
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Lỗi khi xử lý file: {str(e)}'})
    
    return JsonResponse({'status': 'error', 'message': 'Không tìm thấy file'})

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
    
    # subjects = Subject.objects.all()
    curriculum_subjects = Subject.objects.select_related(
        'subject_type', 'department', 'curriculum'
    ).all()
    
    if curriculum_id:
        curriculum_subjects = curriculum_subjects.filter(curriculum_id=curriculum_id)
    if department_id:
        curriculum_subjects = curriculum_subjects.filter(department_id=department_id)
    if subject_group_id:
        curriculum_subjects = curriculum_subjects.filter(subject_group_id=subject_group_id)
    
    # Sắp xếp theo loại môn và thứ tự
    curriculum_subjects = curriculum_subjects.order_by('order_number')
    
    subject_data = []
    for cs in curriculum_subjects:
        semester_allocations = SemesterAllocation.objects.filter(base_subject=cs)
        semester_data = {f'hk{alloc.semester}': float(alloc.credits) for alloc in semester_allocations}
        
        subject_data.append({
            'id': cs.id,  # Sử dụng ID của CurriculumSubject
            'ma_mon_hoc': cs.code,
            'ten_mon_hoc': cs.name,
            'so_tin_chi': float(cs.credits),
            'tong_so_gio': cs.total_hours,
            'ly_thuyet': cs.theory_hours,
            'thuc_hanh': cs.practice_hours,
            'kiem_tra_thi': cs.exam_hours,
            'hk1': semester_data.get('hk1', ''),
            'hk2': semester_data.get('hk2', ''),
            'hk3': semester_data.get('hk3', ''),
            'hk4': semester_data.get('hk4', ''),
            'hk5': semester_data.get('hk5', ''),
            'hk6': semester_data.get('hk6', ''),
            'don_vi': cs.department.name if cs.department else '',
            'giang_vien': '',
            'loai_mon': cs.subject_type.name if cs.subject_type else '',
            'curriculum_id': cs.curriculum.id if cs.curriculum else None,
            'curriculum_name': cs.curriculum.name if cs.curriculum else '',
            'curriculum_code': cs.curriculum.code if cs.curriculum else '',
            'subject_id': cs.id
        })
    
    return JsonResponse(subject_data, safe=False)

def serialize_curriculum_data(data):
    """Serialize curriculum data to ensure JSON compatibility"""
    if isinstance(data, list):
        return [serialize_curriculum_data(item) for item in data]
    elif isinstance(data, dict):
        return {key: serialize_curriculum_data(value) for key, value in data.items()}
    elif hasattr(data, '__dict__'):
        # Handle model instances
        return str(data)
    else:
        return data
    
@csrf_exempt
def api_all_subjects(request):
    """API lấy tất cả môn học (cho dropdown chọn môn học có sẵn)"""
    subjects = Subject.objects.all().values('id', 'code', 'name', 'department__name')
    return JsonResponse(list(subjects), safe=False)

@csrf_exempt
def api_create_subject(request):
    """API tạo môn học mới"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Kiểm tra các trường bắt buộc
            required_fields = ['curriculum_id', 'code', 'name', 'credits', 'subject_type_id']
            for field in required_fields:
                if not data.get(field):
                    return JsonResponse({
                        'status': 'error', 
                        'message': f'Thiếu trường bắt buộc: {field}'
                    })
            
            # Kiểm tra curriculum tồn tại
            try:
                curriculum = Curriculum.objects.get(id=data['curriculum_id'])
            except Curriculum.DoesNotExist:
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Chương trình đào tạo không tồn tại'
                })
            
            # Xử lý department
            department = None
            if data.get('department_id'):
                try:
                    department = Department.objects.get(id=data['department_id'])
                except Department.DoesNotExist:
                    pass
            
            # Xử lý subject_type
            try:
                subject_type = SubjectType.objects.get(id=data['subject_type_id'])
            except SubjectType.DoesNotExist:
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Loại môn học không tồn tại'
                })
            
            # Xử lý subject_group
            subject_group = None
            if data.get('subject_group_id'):
                try:
                    subject_group = SubjectGroup.objects.get(id=data['subject_group_id'])
                except SubjectGroup.DoesNotExist:
                    pass
            
            # Tạo Subject trước (KHÔNG liên kết với curriculum ở đây)
            try:
                subject = Subject.objects.create(
                    code=data['code'],
                    name=data['name'],
                    credits=float(data['credits']),
                    total_hours=int(data.get('total_hours', 0) or 0),
                    theory_hours=int(data.get('theory_hours', 0) or 0),
                    practice_hours=int(data.get('practice_hours', 0) or 0),
                    exam_hours=int(data.get('exam_hours', 0) or 0),
                    department=department,
                    subject_group=subject_group,
                    subject_type=subject_type,
                    prerequisites=data.get('prerequisites', ''),
                    learning_outcomes=data.get('learning_outcomes', ''),
                    description=data.get('description', ''),
                )
            except Exception as e:
                return JsonResponse({
                    'status': 'error', 
                    'message': f'Lỗi khi tạo môn học: {str(e)}'
                })
            
            # # Tạo CurriculumSubject để liên kết
            # try:
            #     curriculum_subject = CurriculumSubject.objects.create(
            #         curriculum=curriculum,
            #         subject=subject,
            #         credits=float(data['credits']),
            #         total_hours=int(data.get('total_hours', 0) or 0),
            #         theory_hours=int(data.get('theory_hours', 0) or 0),
            #         practice_hours=int(data.get('practice_hours', 0) or 0),
            #         exam_hours=int(data.get('exam_hours', 0) or 0),
            #         semester=int(data.get('semester', 0)) if data.get('semester') else None,
            #         order_number=int(data.get('order_number', 0) or 0)
            #     )
            #     print(f"CurriculumSubject created: {curriculum_subject.id}")  # Debug log
            # except Exception as e:
            #     # Nếu tạo CurriculumSubject thất bại, xóa Subject đã tạo
            #     subject.delete()
            #     print(f"Error creating curriculum_subject: {str(e)}")  # Debug log
            #     return JsonResponse({
            #         'status': 'error', 
            #         'message': f'Lỗi khi thêm môn học vào chương trình: {str(e)}'
            #     })
            
            # Tạo phân bố học kỳ
            semester_allocations = data.get('semester_allocations', {})
            for semester_str, credits_value in semester_allocations.items():
                if semester_str.startswith('hk'):
                    semester = int(semester_str.replace('hk', ''))
                    if credits_value and str(credits_value).strip() and float(credits_value) > 0:
                        try:
                            SemesterAllocation.objects.create(
                                base_subject=subject,
                                semester=semester,
                                credits=float(credits_value)
                            )
                        except Exception as e:
                            print(f"Error creating semester allocation: {str(e)}")  # Debug log
            
            return JsonResponse({
                'status': 'success',
                'message': 'Đã tạo môn học thành công',
                'id': subject.id,
                'subject_id': subject.id
            })
            
        except Exception as e:
            print(f"Error creating subject: {str(e)}")
            return JsonResponse({
                'status': 'error', 
                'message': f'Lỗi khi tạo môn học: {str(e)}'
            })
    
    return JsonResponse({
        'status': 'error', 
        'message': 'Method not allowed'
    })
    
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

@csrf_exempt
def api_classes(request):
    """API lấy danh sách lớp học"""
    curriculum_id = request.GET.get('curriculum_id')
    course_id = request.GET.get('course_id')
    is_combined = request.GET.get('is_combined')
    
    classes = Class.objects.select_related('curriculum', 'course')
    
    if curriculum_id:
        classes = classes.filter(curriculum_id=curriculum_id)
    if course_id:
        classes = classes.filter(course_id=course_id)
    if is_combined:
        classes = classes.filter(is_combined=(is_combined.lower() == 'true'))
    
    class_data = list(classes.values('id', 'code', 'name', 'curriculum_id', 'course_id', 'is_combined'))
    return JsonResponse(class_data, safe=False)

@csrf_exempt
def api_combined_classes(request):
    """API lấy danh sách lớp học ghép"""
    curriculum_id = request.GET.get('curriculum_id')
    
    combined_classes = CombinedClass.objects.select_related('curriculum').prefetch_related('classes')
    
    if curriculum_id:
        combined_classes = combined_classes.filter(curriculum_id=curriculum_id)
    
    combined_class_data = []
    for cc in combined_classes:
        combined_class_data.append({
            'id': cc.id,
            'code': cc.code,
            'name': cc.name,
            'curriculum_id': cc.curriculum_id,
            'classes_count': cc.classes.count(),
            'class_codes': [c.code for c in cc.classes.all()]
        })
    
    return JsonResponse(combined_class_data, safe=False)

@csrf_exempt
def api_teaching_assignments(request):
    """API lấy danh sách phân công giảng dạy với thông tin lớp học"""
    instructor_id = request.GET.get('instructor_id')
    curriculum_id = request.GET.get('curriculum_id')
    department_id = request.GET.get('department_id')
    class_id = request.GET.get('class_id')
    combined_class_id = request.GET.get('combined_class_id')
    academic_year = request.GET.get('academic_year')
    semester = request.GET.get('semester')
    
    teaching_assignments = TeachingAssignment.objects.select_related(
        'instructor', 
        'curriculum_subject__name',
        'curriculum_subject__curriculum',
        'class_obj',
        'combined_class'
    )
    
    if instructor_id:
        teaching_assignments = teaching_assignments.filter(instructor_id=instructor_id)
    if curriculum_id:
        teaching_assignments = teaching_assignments.filter(curriculum_subject__curriculum_id=curriculum_id)
    if department_id:
        teaching_assignments = teaching_assignments.filter(
            Q(instructor__department_id=department_id) |
            Q(curriculum_subject__subject__department_id=department_id)
        )
    if class_id:
        teaching_assignments = teaching_assignments.filter(class_obj_id=class_id)
    if combined_class_id:
        teaching_assignments = teaching_assignments.filter(combined_class_id=combined_class_id)
    if academic_year:
        teaching_assignments = teaching_assignments.filter(academic_year=academic_year)
    if semester:
        teaching_assignments = teaching_assignments.filter(semester=semester)
    
    assignments_data = []
    for assignment in teaching_assignments:
        assignment_data = {
            'id': assignment.id,
            'instructor_id': assignment.instructor.id,
            'instructor_name': assignment.instructor.full_name,
            'instructor_code': assignment.instructor.code,
            'subject_id': assignment.curriculum_subject.id,
            'subject_code': assignment.curriculum_subject.code,
            'subject_name': assignment.curriculum_subject.name,
            'curriculum_id': assignment.curriculum_subject.curriculum.id,
            'curriculum_name': assignment.curriculum_subject.curriculum.name,
            'academic_year': assignment.academic_year,
            'semester': assignment.semester,
            'is_main_instructor': assignment.is_main_instructor,
            'student_count': assignment.student_count,
            'teaching_hours': assignment.teaching_hours,
            'class_type': assignment.class_type,
            'class_name': assignment.class_name,
            'class_code': assignment.class_code,
        }
        
        # Thêm thông tin lớp học cụ thể
        if assignment.class_obj:
            assignment_data['class_id'] = assignment.class_obj.id
            assignment_data['class_is_combined'] = assignment.class_obj.is_combined
        elif assignment.combined_class:
            assignment_data['combined_class_id'] = assignment.combined_class.id
        
        assignments_data.append(assignment_data)
    
    return JsonResponse(assignments_data, safe=False)

@csrf_exempt
def api_teaching_statistics(request):
    """API thống kê phân công giảng dạy"""
    # Thống kê theo giảng viên
    instructor_stats = TeachingAssignment.objects.values(
        'instructor__id', 
        'instructor__full_name',
        'instructor__code'
    ).annotate(
        total_assignments=Count('id'),
        total_students=Sum('student_count'),
        total_hours=Sum('teaching_hours'),
        subject_count=Count('curriculum_subject__code', distinct=True),
        regular_class_count=Count(
            Case(
                When(class_obj__isnull=False, then=1),
                output_field=IntegerField(),
            ),
            distinct=True
        ),
        # Đếm lớp học ghép
        combined_class_count=Count(
            Case(
                When(combined_class__isnull=False, then=1),
                output_field=IntegerField(),
            ),
            distinct=True
        )
    ).annotate(
        class_count=F('regular_class_count') + F('combined_class_count')
    )
    
    # Thống kê theo chương trình đào tạo
    curriculum_stats = TeachingAssignment.objects.values(
        'curriculum_subject__curriculum__id',
        'curriculum_subject__curriculum__name',
        'curriculum_subject__curriculum__code'
    ).annotate(
        total_assignments=Count('id'),
        total_instructors=Count('instructor', distinct=True),
        total_subjects=Count('curriculum_subject__code', distinct=True)
    )
    
    # Thống kê theo đơn vị
    department_stats = TeachingAssignment.objects.values(
        'instructor__department__id',
        'instructor__department__name',
        'instructor__department__code'
    ).annotate(
        total_assignments=Count('id'),
        total_instructors=Count('instructor', distinct=True),
        total_hours=Sum('teaching_hours')
    )
    
    return JsonResponse({
        'instructor_statistics': list(instructor_stats),
        'curriculum_statistics': list(curriculum_stats),
        'department_statistics': list(department_stats)
    })

@csrf_exempt
def api_create_teaching_assignment(request):
    """API tạo phân công giảng dạy mới"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Kiểm tra các trường bắt buộc
            required_fields = ['instructor_id', 'curriculum_subject_id', 'academic_year', 'semester']
            for field in required_fields:
                if not data.get(field):
                    return JsonResponse({
                        'status': 'error', 
                        'message': f'Thiếu trường bắt buộc: {field}'
                    })
            
            # Kiểm tra xem có class_obj hay combined_class
            if not data.get('class_obj_id') and not data.get('combined_class_id'):
                return JsonResponse({
                    'status': 'error', 
                    'message': 'Phải chọn lớp học thường hoặc lớp học ghép'
                })
            
            # Tạo phân công giảng dạy
            teaching_assignment = TeachingAssignment.objects.create(
                instructor_id=data['instructor_id'],
                curriculum_subject_id=data['curriculum_subject_id'],
                class_obj_id=data.get('class_obj_id'),
                combined_class_id=data.get('combined_class_id'),
                academic_year=data['academic_year'],
                semester=data['semester'],
                is_main_instructor=data.get('is_main_instructor', True),
                student_count=data.get('student_count', 0),
                teaching_hours=data.get('teaching_hours', 0)
            )
            
            return JsonResponse({
                'status': 'success',
                'message': 'Đã tạo phân công giảng dạy thành công',
                'id': teaching_assignment.id
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error', 
                'message': f'Lỗi khi tạo phân công giảng dạy: {str(e)}'
            })
    
    return JsonResponse({
        'status': 'error', 
        'message': 'Method not allowed'
    })
    
class TeachingManagementView(View):
    """View quản lý phân công giảng dạy"""
    template_name = 'products/teaching_management.html'
    
    def get(self, request):
        # Lấy dữ liệu cho các dropdown
        instructors = Instructor.objects.all().values('id', 'code', 'full_name', 'department__name')
        curricula = Curriculum.objects.all().values('id', 'code', 'name', 'academic_year')
        departments = Department.objects.all().values('id', 'code', 'name')
        courses = Course.objects.all().values('id', 'code', 'name')
        subject_types = SubjectType.objects.all().values('id', 'code', 'name')
        majors = Major.objects.all().values('id', 'code', 'name')
        
        context = {
            'instructors': list(instructors),
            'curricula': list(curricula),
            'departments': list(departments),
            'courses': list(courses),
            'subject_types': list(subject_types),
            'majors': list(majors),
        }
        
        return render(request, self.template_name, context)

@csrf_exempt
def api_instructors(request):
    """API lấy danh sách giảng viên"""
    instructors = Instructor.objects.all().values('id', 'code', 'full_name', 'department__name')
    return JsonResponse(list(instructors), safe=False)

@csrf_exempt
def api_create_class(request):
    """API tạo lớp học mới"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Kiểm tra các trường bắt buộc
            required_fields = ['code', 'name', 'curriculum_id', 'course_id']
            for field in required_fields:
                if not data.get(field):
                    return JsonResponse({
                        'status': 'error', 
                        'message': f'Thiếu trường bắt buộc: {field}'
                    })
            
            # Xử lý trường ngày tháng - chuyển chuỗi rỗng thành None
            start_date = data.get('start_date')
            if start_date == '':
                start_date = None
                
            end_date = data.get('end_date')
            if end_date == '':
                end_date = None
            
            # Xử lý trường boolean
            is_combined = data.get('is_combined', False)
            if isinstance(is_combined, str):
                is_combined = is_combined.lower() == 'true'
            
            # Xử lý combined_class_code - chuỗi rỗng thành None
            combined_class_code = data.get('combined_class_code')
            if combined_class_code == '':
                combined_class_code = None
            
            # Tạo lớp học
            class_obj = Class.objects.create(
                code=data.get('code'),
                name=data.get('name'),
                curriculum_id=data.get('curriculum_id'),
                course_id=data.get('course_id'),
                start_date=start_date,
                end_date=end_date,
                is_combined=is_combined,
                combined_class_code=combined_class_code,
                description=data.get('description')
            )
            
            return JsonResponse({
                'status': 'success',
                'message': 'Đã tạo lớp học thành công',
                'id': class_obj.id
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error', 
                'message': f'Lỗi khi tạo lớp học: {str(e)}'
            })
    
    return JsonResponse({
        'status': 'error', 
        'message': 'Method not allowed'
    })

# @csrf_exempt
# def api_curriculum_subjects(request):
#     """API lấy danh sách môn học trong chương trình"""
#     curriculum_id = request.GET.get('curriculum_id')
    
#     curriculum_subjects = CurriculumSubject.objects.select_related(
#         'subject', 'curriculum'
#     )
    
#     if curriculum_id:
#         curriculum_subjects = curriculum_subjects.filter(curriculum_id=curriculum_id)
    
#     subjects_data = []
#     for cs in curriculum_subjects:
#         subjects_data.append({
#             'id': cs.id,
#             'subject_id': cs.subject.id,
#             'subject_code': cs.subject.code,
#             'subject_name': cs.subject.name,
#             'curriculum_id': cs.curriculum.id,
#             'curriculum_name': cs.curriculum.name,
#             'credits': float(cs.credits)
#         })
    
#     return JsonResponse(subjects_data, safe=False)

@csrf_exempt
def api_create_combined_class(request):
    """API tạo lớp học ghép mới"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Kiểm tra các trường bắt buộc
            required_fields = ['code', 'name', 'curriculum_id', 'classes']
            for field in required_fields:
                if not data.get(field):
                    return JsonResponse({
                        'status': 'error', 
                        'message': f'Thiếu trường bắt buộc: {field}'
                    })
            
             # Xử lý description - chuỗi rỗng thành None
            description = data.get('description')
            if description == '':
                description = None
            
            # Tạo lớp học ghép
            combined_class = CombinedClass.objects.create(
                code=data.get('code'),
                name=data.get('name'),
                curriculum_id=data.get('curriculum_id'),
                description=description
            )
            
            # Thêm các lớp thành phần
            classes = Class.objects.filter(id__in=data.get('classes', []))
            combined_class.classes.set(classes)
            
            return JsonResponse({
                'status': 'success',
                'message': 'Đã tạo lớp học ghép thành công',
                'id': combined_class.id
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error', 
                'message': f'Lỗi khi tạo lớp học ghép: {str(e)}'
            })
    
    return JsonResponse({
        'status': 'error', 
        'message': 'Method not allowed'
    })

# Thêm import cần thiết
import pandas as pd
import io
from django.core.files.base import ContentFile

class ImportTeachingDataView(View):
    class ImportTeachingDataView(View):
        def get(self, request, object_type):
            """Tải file Excel mẫu cho từng loại đối tượng với sheet hướng dẫn"""
            try:
                # Tạo workbook
                output = io.BytesIO()
                
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    # Tạo sheet dữ liệu mẫu
                    if object_type == 'class':
                        sample_data = self.get_class_template()
                        filename = "mau_import_lop_hoc.xlsx"
                        df = pd.DataFrame(sample_data)
                        df.to_excel(writer, index=False, sheet_name='Dữ liệu mẫu')
                        
                        # Tạo sheet hướng dẫn cho lớp học
                        self.create_class_guide_sheet(writer)
                        
                    elif object_type == 'combined-class':
                        sample_data = self.get_combined_class_template()
                        filename = "mau_import_lop_hoc_ghep.xlsx"
                        df = pd.DataFrame(sample_data)
                        df.to_excel(writer, index=False, sheet_name='Dữ liệu mẫu')
                        
                        # Tạo sheet hướng dẫn cho lớp học ghép
                        self.create_combined_class_guide_sheet(writer)
                        
                    elif object_type == 'teaching-assignment':
                        sample_data = self.get_teaching_assignment_template()
                        filename = "mau_import_phan_cong_giang_day.xlsx"
                        df = pd.DataFrame(sample_data)
                        df.to_excel(writer, index=False, sheet_name='Dữ liệu mẫu')
                        
                        # Tạo sheet hướng dẫn cho phân công giảng dạy
                        self.create_teaching_assignment_guide_sheet(writer)
                        
                    else:
                        return JsonResponse({'status': 'error', 'message': 'Loại đối tượng không hợp lệ'})
                
                output.seek(0)
                
                # Trả về file để download
                response = HttpResponse(
                    output.getvalue(),
                    content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                response['Content-Length'] = len(output.getvalue())
                
                return response
            except Exception as e:
                return JsonResponse({'status': 'error', 'message': f"Lỗi tạo file mẫu: {str(e)}"})
    
    def create_class_guide_sheet(self, writer):
        """Tạo sheet hướng dẫn cho import lớp học"""
        guide_data = {}
        
        # Lấy danh sách chương trình
        curricula = Curriculum.objects.all().values('code', 'name', 'academic_year')
        guide_data['Chương trình đào tạo'] = {
            'Mã chương trình': [c['code'] for c in curricula],
            'Tên chương trình': [c['name'] for c in curricula],
            'Năm học': [c['academic_year'] for c in curricula]
        }
        
        # Lấy danh sách khóa học
        courses = Course.objects.all().values('code', 'name', 'curriculum__code')
        guide_data['Khóa học'] = {
            'Mã khóa học': [c['code'] for c in courses],
            'Tên khóa học': [c['name'] for c in courses],
            'Mã chương trình': [c['curriculum__code'] for c in courses]
        }
        
        # Lấy danh sách lớp học hiện có
        classes = Class.objects.all().values('code', 'name', 'curriculum__code', 'course__code')
        guide_data['Lớp học hiện có'] = {
            'Mã lớp': [c['code'] for c in classes],
            'Tên lớp': [c['name'] for c in classes],
            'Mã chương trình': [c['curriculum__code'] for c in classes],
            'Mã khóa học': [c['course__code'] for c in classes]
        }
        
        # Tạo sheet hướng dẫn
        workbook = writer.book
        worksheet = workbook.create_sheet("Hướng dẫn nhập liệu")
        
        row = 1
        for section, data in guide_data.items():
            # Tiêu đề section
            worksheet.cell(row=row, column=1, value=section.upper())
            worksheet.cell(row=row, column=1).font = pd.ExcelWriter().book.add_format({'bold': True})
            row += 1
            
            # Tiêu đề cột
            col = 1
            for col_name in data.keys():
                worksheet.cell(row=row, column=col, value=col_name)
                col += 1
            row += 1
            
            # Dữ liệu
            max_rows = max(len(values) for values in data.values())
            for i in range(max_rows):
                col = 1
                for col_name, values in data.items():
                    if i < len(values):
                        worksheet.cell(row=row, column=col, value=values[i])
                    col += 1
                row += 1
            
            row += 2  # Thêm khoảng cách giữa các section
        
        # Thêm ghi chú
        worksheet.cell(row=row, column=1, value="LƯU Ý QUAN TRỌNG:")
        worksheet.cell(row=row, column=1).font = pd.ExcelWriter().book.add_format({'bold': True})
        row += 1
        
        notes = [
            "1. Chỉ nhập dữ liệu vào sheet 'Dữ liệu mẫu'",
            "2. Các cột có dấu * là bắt buộc",
            "3. Sử dụng các giá trị từ sheet này để đảm bảo tính nhất quán",
            "4. Mã lớp không được trùng với các lớp đã có trong hệ thống",
            "5. Ngày tháng nhập theo định dạng YYYY-MM-DD (ví dụ: 2023-09-01)"
        ]
        
        for note in notes:
            worksheet.cell(row=row, column=1, value=note)
            row += 1
    
    def create_combined_class_guide_sheet(self, writer):
        """Tạo sheet hướng dẫn cho import lớp học ghép"""
        guide_data = {}
        
        # Lấy danh sách chương trình
        curricula = Curriculum.objects.all().values('code', 'name', 'academic_year')
        guide_data['Chương trình đào tạo'] = {
            'Mã chương trình': [c['code'] for c in curricula],
            'Tên chương trình': [c['name'] for c in curricula],
            'Năm học': [c['academic_year'] for c in curricula]
        }
        
        # Lấy danh sách lớp học có thể ghép
        classes = Class.objects.filter(is_combined=False).values('code', 'name', 'curriculum__code')
        guide_data['Lớp học có thể ghép'] = {
            'Mã lớp': [c['code'] for c in classes],
            'Tên lớp': [c['name'] for c in classes],
            'Mã chương trình': [c['curriculum__code'] for c in classes]
        }
        
        # Lấy danh sách lớp học ghép hiện có
        combined_classes = CombinedClass.objects.all().values('code', 'name', 'curriculum__code')
        guide_data['Lớp học ghép hiện có'] = {
            'Mã lớp ghép': [c['code'] for c in combined_classes],
            'Tên lớp ghép': [c['name'] for c in combined_classes],
            'Mã chương trình': [c['curriculum__code'] for c in combined_classes]
        }
        
        # Tạo sheet hướng dẫn
        workbook = writer.book
        worksheet = workbook.create_sheet("Hướng dẫn nhập liệu")
        
        row = 1
        for section, data in guide_data.items():
            # Tiêu đề section
            worksheet.cell(row=row, column=1, value=section.upper())
            worksheet.cell(row=row, column=1).font = pd.ExcelWriter().book.add_format({'bold': True})
            row += 1
            
            # Tiêu đề cột
            col = 1
            for col_name in data.keys():
                worksheet.cell(row=row, column=col, value=col_name)
                col += 1
            row += 1
            
            # Dữ liệu
            max_rows = max(len(values) for values in data.values())
            for i in range(max_rows):
                col = 1
                for col_name, values in data.items():
                    if i < len(values):
                        worksheet.cell(row=row, column=col, value=values[i])
                    col += 1
                row += 1
            
            row += 2  # Thêm khoảng cách giữa các section
        
        # Thêm ghi chú
        worksheet.cell(row=row, column=1, value="LƯU Ý QUAN TRỌNG:")
        worksheet.cell(row=row, column=1).font = pd.ExcelWriter().book.add_format({'bold': True})
        row += 1
        
        notes = [
            "1. Chỉ nhập dữ liệu vào sheet 'Dữ liệu mẫu'",
            "2. Các cột có dấu * là bắt buộc",
            "3. Sử dụng các giá trị từ sheet này để đảm bảo tính nhất quán",
            "4. Mã lớp ghép không được trùng với các lớp ghép đã có",
            "5. Các mã lớp thành phần phân cách bằng dấu phẩy (ví dụ: DHTI001,DHTI002)",
            "6. Các lớp thành phần phải thuộc cùng chương trình đào tạo"
        ]
        
        for note in notes:
            worksheet.cell(row=row, column=1, value=note)
            row += 1
    
    def create_teaching_assignment_guide_sheet(self, writer):
        """Tạo sheet hướng dẫn cho import phân công giảng dạy"""
        guide_data = {}
        
        # Lấy danh sách giảng viên
        instructors = Instructor.objects.all().values('code', 'full_name', 'department__name')
        guide_data['Giảng viên'] = {
            'Mã giảng viên': [i['code'] for i in instructors],
            'Họ tên': [i['full_name'] for i in instructors],
            'Khoa': [i['department__name'] for i in instructors]
        }
        
        # Lấy danh sách môn học
        curriculum_subjects = Subject.objects.select_related('code', 'curriculum').all()
        guide_data['Môn học'] = {
            'Mã môn học': [cs.code for cs in curriculum_subjects],
            'Tên môn học': [cs.name for cs in curriculum_subjects],
            'Mã chương trình': [cs.curriculum.code for cs in curriculum_subjects]
        }
        
        # Lấy danh sách lớp học thường
        classes = Class.objects.all().values('code', 'name', 'curriculum__code')
        guide_data['Lớp học thường'] = {
            'Mã lớp': [c['code'] for c in classes],
            'Tên lớp': [c['name'] for c in classes],
            'Mã chương trình': [c['curriculum__code'] for c in classes]
        }
        
        # Lấy danh sách lớp học ghép
        combined_classes = CombinedClass.objects.all().values('code', 'name', 'curriculum__code')
        guide_data['Lớp học ghép'] = {
            'Mã lớp ghép': [c['code'] for c in combined_classes],
            'Tên lớp ghép': [c['name'] for c in combined_classes],
            'Mã chương trình': [c['curriculum__code'] for c in combined_classes]
        }
        
        # Danh sách loại lớp
        guide_data['Loại lớp'] = {
            'Giá trị hợp lệ': ['Thường', 'Ghép']
        }
        
        # Danh sách học kỳ
        guide_data['Học kỳ'] = {
            'Giá trị hợp lệ': [str(i) for i in range(1, 13)]
        }
        
        # Tạo sheet hướng dẫn
        workbook = writer.book
        worksheet = workbook.create_sheet("Hướng dẫn nhập liệu")
        
        row = 1
        for section, data in guide_data.items():
            # Tiêu đề section
            worksheet.cell(row=row, column=1, value=section.upper())
            worksheet.cell(row=row, column=1).font = pd.ExcelWriter().book.add_format({'bold': True})
            row += 1
            
            # Tiêu đề cột
            col = 1
            for col_name in data.keys():
                worksheet.cell(row=row, column=col, value=col_name)
                col += 1
            row += 1
            
            # Dữ liệu
            max_rows = max(len(values) for values in data.values())
            for i in range(max_rows):
                col = 1
                for col_name, values in data.items():
                    if i < len(values):
                        worksheet.cell(row=row, column=col, value=values[i])
                    col += 1
                row += 1
            
            row += 2  # Thêm khoảng cách giữa các section
        
        # Thêm ghi chú
        worksheet.cell(row=row, column=1, value="LƯU Ý QUAN TRỌNG:")
        worksheet.cell(row=row, column=1).font = pd.ExcelWriter().book.add_format({'bold': True})
        row += 1
        
        notes = [
            "1. Chỉ nhập dữ liệu vào sheet 'Dữ liệu mẫu'",
            "2. Các cột có dấu * là bắt buộc",
            "3. Sử dụng các giá trị từ sheet này để đảm bảo tính nhất quán",
            "4. Loại lớp phải là 'Thường' hoặc 'Ghép'",
            "5. Học kỳ phải là số từ 1 đến 12",
            "6. Năm học theo định dạng YYYY-YYYY (ví dụ: 2023-2024)",
            "7. Là giảng viên chính: 'Có' hoặc 'Không'"
        ]
        
        for note in notes:
            worksheet.cell(row=row, column=1, value=note)
            row += 1
    
    def post(self, request, object_type):
        """Xử lý import file Excel với chức năng chọn sheet"""
        try:
            if request.FILES.get('excel_file'):
                excel_file = request.FILES['excel_file']
                selected_sheet = request.POST.get('selected_sheet', '')
                
                # Kiểm tra định dạng file
                if not excel_file.name.endswith(('.xlsx', '.xls')):
                    return JsonResponse({'status': 'error', 'message': 'File phải có định dạng Excel (.xlsx hoặc .xls)'})
                
                # Kiểm tra kích thước file (tối đa 10MB)
                if excel_file.size > 10 * 1024 * 1024:
                    return JsonResponse({'status': 'error', 'message': 'File không được vượt quá 10MB'})
                
                try:
                    # Đọc file Excel để lấy danh sách sheet
                    excel_file.seek(0)
                    xls = pd.ExcelFile(excel_file)
                    sheet_names = xls.sheet_names
                    
                    # Nếu không có sheet được chọn, sử dụng sheet đầu tiên
                    if not selected_sheet and sheet_names:
                        selected_sheet = sheet_names[0]
                    
                    # Đọc sheet được chọn
                    df = pd.read_excel(excel_file, sheet_name=selected_sheet)
                    print(f"File imported successfully, sheet: {selected_sheet}, shape: {df.shape}")
                    
                except Exception as e:
                    return JsonResponse({'status': 'error', 'message': f'Không thể đọc file Excel: {str(e)}'})
                
                # Xử lý dữ liệu theo loại đối tượng
                if object_type == 'class':
                    result = self.process_class_import(df, request.user, excel_file, selected_sheet)
                elif object_type == 'combined-class':
                    result = self.process_combined_class_import(df, request.user, excel_file, selected_sheet)
                elif object_type == 'teaching-assignment':
                    result = self.process_teaching_assignment_import(df, request.user, excel_file, selected_sheet)
                else:
                    return JsonResponse({'status': 'error', 'message': 'Loại đối tượng không hợp lệ'})
                
                if result['status'] == 'success':
                    return JsonResponse({
                        'status': 'success', 
                        'message': result['message'],
                        'data': result.get('processed_data', []),
                        'errors': result.get('errors', []),
                        'sheet_used': selected_sheet
                    })
                else:
                    return JsonResponse({'status': 'error', 'message': result['message']})
                    
            else:
                return JsonResponse({'status': 'error', 'message': 'Không tìm thấy file'})
                
        except Exception as e:
            print(f"Error in import: {str(e)}")
            return JsonResponse({'status': 'error', 'message': f'Lỗi khi xử lý file: {str(e)}'})
    
    def get_sheet_names(self, excel_file):
        """Lấy danh sách các sheet trong file Excel"""
        try:
            excel_file.seek(0)
            xls = pd.ExcelFile(excel_file)
            return xls.sheet_names
        except Exception as e:
            print(f"Error getting sheet names: {str(e)}")
            return []
    
    def get_class_template(self):
        """Tạo template cho import lớp học"""
        return {
            'Mã lớp*': ['DHTI001', 'DHTI002', 'DHTI003'],
            'Tên lớp*': ['Lớp Công nghệ Thông tin 001', 'Lớp Công nghệ Thông tin 002', 'Lớp Công nghệ Thông tin 003'],
            'Mã chương trình*': ['CNTT_2023', 'CNTT_2023', 'CNTT_2023'],
            'Mã khóa học*': ['K2023', 'K2023', 'K2023'],
            'Ngày bắt đầu': ['2023-09-01', '2023-09-01', '2023-09-01'],
            'Ngày kết thúc': ['2027-06-30', '2027-06-30', '2027-06-30'],
            'Là lớp ghép': ['Không', 'Không', 'Có'],
            'Mã lớp ghép (nếu có)': ['', '', 'GHÉP001'],
            'Mô tả': ['', '', 'Lớp ghép cho các môn chung']
        }
    
    def get_combined_class_template(self):
        """Tạo template cho import lớp học ghép"""
        return {
            'Mã lớp ghép*': ['GHÉP001', 'GHÉP002'],
            'Tên lớp ghép*': ['Lớp ghép Công nghệ Thông tin', 'Lớp ghép Kỹ thuật phần mềm'],
            'Mã chương trình*': ['CNTT_2023', 'KTPM_2023'],
            'Mã các lớp thành phần*': ['DHTI001,DHTI002', 'DHTI003,DHTI004'],
            'Mô tả': ['Lớp ghép cho các môn đại cương', 'Lớp ghép cho các môn chuyên ngành']
        }
    
    def get_teaching_assignment_template(self):
        """Tạo template cho import phân công giảng dạy"""
        return {
            'Mã giảng viên*': ['GV001', 'GV002', 'GV001'],
            'Mã môn học*': ['MH001', 'MH002', 'MH003'],
            'Mã lớp*': ['DHTI001', 'DHTI002', 'GHÉP001'],
            'Loại lớp*': ['Thường', 'Thường', 'Ghép'],
            'Năm học*': ['2023-2024', '2023-2024', '2023-2024'],
            'Học kỳ*': [1, 1, 2],
            'Là giảng viên chính*': ['Có', 'Có', 'Không'],
            'Số lượng sinh viên': [40, 35, 80],
            'Số giờ giảng dạy': [45, 60, 30]
        }
    
    def process_class_import(self, df, user, excel_file, sheet_name):
        """Xử lý import lớp học"""
        try:
            created_count = 0
            updated_count = 0
            errors = []
            processed_data = []
            
            # Kiểm tra cấu trúc file
            required_columns = ['Mã lớp*', 'Tên lớp*', 'Mã chương trình*', 'Mã khóa học*']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return {
                    'status': 'error', 
                    'message': f'File thiếu các cột bắt buộc: {", ".join(missing_columns)}'
                }
            
            for index, row in df.iterrows():
                try:
                    # Bỏ qua các dòng trống
                    if pd.isna(row.get('Mã lớp*')) or str(row.get('Mã lớp*')).strip() in ['', 'Mã lớp*', 'nan']:
                        continue
                    
                    # Chuẩn hóa dữ liệu
                    code = str(row.get('Mã lớp*')).strip()
                    name = str(row.get('Tên lớp*')).strip()
                    curriculum_code = str(row.get('Mã chương trình*')).strip()
                    course_code = str(row.get('Mã khóa học*')).strip()
                    
                    if not code or not name or not curriculum_code or not course_code:
                        errors.append(f"Dòng {index + 2}: Thiếu thông tin bắt buộc")
                        continue
                    
                    # Tìm curriculum và course
                    try:
                        curriculum = Curriculum.objects.get(code=curriculum_code)
                    except Curriculum.DoesNotExist:
                        errors.append(f"Dòng {index + 2}: Không tìm thấy chương trình với mã '{curriculum_code}'")
                        continue
                    
                    try:
                        course = Course.objects.get(code=course_code)
                    except Course.DoesNotExist:
                        errors.append(f"Dòng {index + 2}: Không tìm thấy khóa học với mã '{course_code}'")
                        continue
                    
                    # Xử lý ngày tháng
                    start_date = None
                    end_date = None
                    
                    start_date_str = str(row.get('Ngày bắt đầu', '')).strip()
                    if start_date_str and start_date_str not in ['', 'nan']:
                        try:
                            start_date = pd.to_datetime(start_date_str).date()
                        except:
                            errors.append(f"Dòng {index + 2}: Định dạng ngày bắt đầu không hợp lệ: {start_date_str}")
                    
                    end_date_str = str(row.get('Ngày kết thúc', '')).strip()
                    if end_date_str and end_date_str not in ['', 'nan']:
                        try:
                            end_date = pd.to_datetime(end_date_str).date()
                        except:
                            errors.append(f"Dòng {index + 2}: Định dạng ngày kết thúc không hợp lệ: {end_date_str}")
                    
                    # Xử lý lớp ghép
                    is_combined_str = str(row.get('Là lớp ghép', 'Không')).strip()
                    is_combined = is_combined_str.lower() in ['có', 'yes', 'true', '1']
                    
                    combined_class_code = str(row.get('Mã lớp ghép (nếu có)', '')).strip()
                    if combined_class_code in ['', 'nan']:
                        combined_class_code = None
                    
                    description = str(row.get('Mô tả', '')).strip()
                    if description in ['', 'nan']:
                        description = None
                    
                    # Tạo hoặc cập nhật lớp học
                    class_obj, created = Class.objects.update_or_create(
                        code=code,
                        defaults={
                            'name': name,
                            'curriculum': curriculum,
                            'course': course,
                            'start_date': start_date,
                            'end_date': end_date,
                            'is_combined': is_combined,
                            'combined_class_code': combined_class_code,
                            'description': description
                        }
                    )
                    
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
                    
                    processed_data.append({
                        'code': class_obj.code,
                        'name': class_obj.name,
                        'curriculum': curriculum.name,
                        'course': course.name
                    })
                    
                except Exception as e:
                    errors.append(f"Dòng {index + 2}: {str(e)}")
            
            # Lưu lịch sử import
            ImportHistory.objects.create(
                file_name=excel_file.name,
                file_size=excel_file.size,
                imported_by=user,
                record_count=len(processed_data),
                status='success' if not errors else 'partial',
                errors=errors if errors else None,
                additional_info=f"Sheet được sử dụng: {sheet_name}"
            )
            
            return {
                'status': 'success',
                'message': f'Import thành công: {created_count} lớp học được tạo, {updated_count} lớp học được cập nhật',
                'created_count': created_count,
                'updated_count': updated_count,
                'processed_data': processed_data,
                'errors': errors
            }
            
        except Exception as e:
            print(f"Error in process_class_import: {str(e)}")
            return {'status': 'error', 'message': f'Lỗi xử lý dữ liệu: {str(e)}'}
    
    def process_combined_class_import(self, df, user, excel_file, sheet_name):
        """Xử lý import lớp học ghép"""
        try:
            created_count = 0
            updated_count = 0
            errors = []
            processed_data = []
            
            # Kiểm tra cấu trúc file
            required_columns = ['Mã lớp ghép*', 'Tên lớp ghép*', 'Mã chương trình*', 'Mã các lớp thành phần*']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return {
                    'status': 'error', 
                    'message': f'File thiếu các cột bắt buộc: {", ".join(missing_columns)}'
                }
            
            for index, row in df.iterrows():
                try:
                    # Bỏ qua các dòng trống
                    if pd.isna(row.get('Mã lớp ghép*')) or str(row.get('Mã lớp ghép*')).strip() in ['', 'Mã lớp ghép*', 'nan']:
                        continue
                    
                    # Chuẩn hóa dữ liệu
                    code = str(row.get('Mã lớp ghép*')).strip()
                    name = str(row.get('Tên lớp ghép*')).strip()
                    curriculum_code = str(row.get('Mã chương trình*')).strip()
                    classes_codes_str = str(row.get('Mã các lớp thành phần*')).strip()
                    
                    if not code or not name or not curriculum_code or not classes_codes_str:
                        errors.append(f"Dòng {index + 2}: Thiếu thông tin bắt buộc")
                        continue
                    
                    # Tìm curriculum
                    try:
                        curriculum = Curriculum.objects.get(code=curriculum_code)
                    except Curriculum.DoesNotExist:
                        errors.append(f"Dòng {index + 2}: Không tìm thấy chương trình với mã '{curriculum_code}'")
                        continue
                    
                    # Xử lý các lớp thành phần
                    class_codes = [c.strip() for c in classes_codes_str.split(',')]
                    classes = []
                    for class_code in class_codes:
                        try:
                            class_obj = Class.objects.get(code=class_code)
                            classes.append(class_obj)
                        except Class.DoesNotExist:
                            errors.append(f"Dòng {index + 2}: Không tìm thấy lớp với mã '{class_code}'")
                    
                    if not classes:
                        errors.append(f"Dòng {index + 2}: Không có lớp thành phần hợp lệ")
                        continue
                    
                    description = str(row.get('Mô tả', '')).strip()
                    if description in ['', 'nan']:
                        description = None
                    
                    # Tạo hoặc cập nhật lớp học ghép
                    combined_class, created = CombinedClass.objects.update_or_create(
                        code=code,
                        defaults={
                            'name': name,
                            'curriculum': curriculum,
                            'description': description
                        }
                    )
                    
                    # Cập nhật các lớp thành phần
                    combined_class.classes.set(classes)
                    
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
                    
                    processed_data.append({
                        'code': combined_class.code,
                        'name': combined_class.name,
                        'curriculum': curriculum.name,
                        'classes_count': len(classes)
                    })
                    
                except Exception as e:
                    errors.append(f"Dòng {index + 2}: {str(e)}")
            
            # Lưu lịch sử import
            ImportHistory.objects.create(
                file_name=excel_file.name,
                file_size=excel_file.size,
                imported_by=user,
                record_count=len(processed_data),
                status='success' if not errors else 'partial',
                errors=errors if errors else None,
                additional_info=f"Sheet được sử dụng: {sheet_name}"
            )
            
            return {
                'status': 'success',
                'message': f'Import thành công: {created_count} lớp ghép được tạo, {updated_count} lớp ghép được cập nhật',
                'created_count': created_count,
                'updated_count': updated_count,
                'processed_data': processed_data,
                'errors': errors
            }
            
        except Exception as e:
            print(f"Error in process_combined_class_import: {str(e)}")
            return {'status': 'error', 'message': f'Lỗi xử lý dữ liệu: {str(e)}'}
    
    def process_teaching_assignment_import(self, df, user, excel_file, sheet_name):
        """Xử lý import phân công giảng dạy"""
        try:
            created_count = 0
            updated_count = 0
            errors = []
            processed_data = []
            
            # Kiểm tra cấu trúc file
            required_columns = ['Mã giảng viên*', 'Mã môn học*', 'Mã lớp*', 'Loại lớp*', 'Năm học*', 'Học kỳ*']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return {
                    'status': 'error', 
                    'message': f'File thiếu các cột bắt buộc: {", ".join(missing_columns)}'
                }
            
            for index, row in df.iterrows():
                try:
                    # Bỏ qua các dòng trống
                    if pd.isna(row.get('Mã giảng viên*')) or str(row.get('Mã giảng viên*')).strip() in ['', 'Mã giảng viên*', 'nan']:
                        continue
                    
                    # Chuẩn hóa dữ liệu
                    instructor_code = str(row.get('Mã giảng viên*')).strip()
                    subject_code = str(row.get('Mã môn học*')).strip()
                    class_code = str(row.get('Mã lớp*')).strip()
                    class_type = str(row.get('Loại lớp*')).strip()
                    academic_year = str(row.get('Năm học*')).strip()
                    semester = str(row.get('Học kỳ*')).strip()
                    
                    if not instructor_code or not subject_code or not class_code or not class_type or not academic_year or not semester:
                        errors.append(f"Dòng {index + 2}: Thiếu thông tin bắt buộc")
                        continue
                    
                    # Tìm giảng viên
                    try:
                        instructor = Instructor.objects.get(code=instructor_code)
                    except Instructor.DoesNotExist:
                        errors.append(f"Dòng {index + 2}: Không tìm thấy giảng viên với mã '{instructor_code}'")
                        continue
                    
                    # Tìm môn học (CurriculumSubject)
                    try:
                        curriculum_subjects = Subject.objects.get(
                            code=subject_code
                        )
                    except Subject.DoesNotExist:
                        errors.append(f"Dòng {index + 2}: Không tìm thấy môn học với mã '{subject_code}'")
                        continue
                    except Subject.MultipleObjectsReturned:
                        curriculum_subjects = Subject.objects.filter(
                            code=subject_code
                        )
                        curriculum_subject = curriculum_subjects.first()
                        errors.append(f"Dòng {index + 2}: Có nhiều môn học với mã '{subject_code}', sử dụng môn học đầu tiên")
                    
                    # Tìm lớp học
                    class_obj = None
                    combined_class = None
                    
                    if class_type.lower() in ['thường', 'regular', 'thuong']:
                        try:
                            class_obj = Class.objects.get(code=class_code)
                        except Class.DoesNotExist:
                            errors.append(f"Dòng {index + 2}: Không tìm thấy lớp thường với mã '{class_code}'")
                            continue
                    elif class_type.lower() in ['ghép', 'combined', 'ghep']:
                        try:
                            combined_class = CombinedClass.objects.get(code=class_code)
                        except CombinedClass.DoesNotExist:
                            errors.append(f"Dòng {index + 2}: Không tìm thấy lớp ghép với mã '{class_code}'")
                            continue
                    else:
                        errors.append(f"Dòng {index + 2}: Loại lớp không hợp lệ: {class_type}. Phải là 'Thường' hoặc 'Ghép'")
                        continue
                    
                    # Xử lý học kỳ
                    try:
                        semester = int(semester)
                    except ValueError:
                        errors.append(f"Dòng {index + 2}: Học kỳ phải là số: {semester}")
                        continue
                    
                    # Xử lý giảng viên chính
                    is_main_instructor_str = str(row.get('Là giảng viên chính*', 'Có')).strip()
                    is_main_instructor = is_main_instructor_str.lower() in ['có', 'yes', 'true', '1']
                    
                    # Xử lý số lượng sinh viên và giờ giảng dạy
                    student_count = 0
                    teaching_hours = 0
                    
                    try:
                        student_count = int(row.get('Số lượng sinh viên', 0))
                    except (ValueError, TypeError):
                        pass
                    
                    try:
                        teaching_hours = int(row.get('Số giờ giảng dạy', 0))
                    except (ValueError, TypeError):
                        pass
                    
                    # Tạo hoặc cập nhật phân công giảng dạy
                    if class_obj:
                        # Phân công cho lớp thường
                        teaching_assignment, created = TeachingAssignment.objects.update_or_create(
                            instructor=instructor,
                            curriculum_subject=curriculum_subject,
                            class_obj=class_obj,
                            academic_year=academic_year,
                            semester=semester,
                            defaults={
                                'is_main_instructor': is_main_instructor,
                                'student_count': student_count,
                                'teaching_hours': teaching_hours
                            }
                        )
                    else:
                        # Phân công cho lớp ghép
                        teaching_assignment, created = TeachingAssignment.objects.update_or_create(
                            instructor=instructor,
                            curriculum_subject=curriculum_subject,
                            combined_class=combined_class,
                            academic_year=academic_year,
                            semester=semester,
                            defaults={
                                'is_main_instructor': is_main_instructor,
                                'student_count': student_count,
                                'teaching_hours': teaching_hours
                            }
                        )
                    
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
                    
                    processed_data.append({
                        'instructor': instructor.full_name,
                        'subject': curriculum_subject.name,
                        'class_code': class_code,
                        'academic_year': academic_year,
                        'semester': semester
                    })
                    
                except Exception as e:
                    errors.append(f"Dòng {index + 2}: {str(e)}")
            
            # Lưu lịch sử import
            ImportHistory.objects.create(
                file_name=excel_file.name,
                file_size=excel_file.size,
                imported_by=user,
                record_count=len(processed_data),
                status='success' if not errors else 'partial',
                errors=errors if errors else None,
                additional_info=f"Sheet được sử dụng: {sheet_name}"
            )
            
            return {
                'status': 'success',
                'message': f'Import thành công: {created_count} phân công được tạo, {updated_count} phân công được cập nhật',
                'created_count': created_count,
                'updated_count': updated_count,
                'processed_data': processed_data,
                'errors': errors
            }
            
        except Exception as e:
            print(f"Error in process_teaching_assignment_import: {str(e)}")
            return {'status': 'error', 'message': f'Lỗi xử lý dữ liệu: {str(e)}'}
