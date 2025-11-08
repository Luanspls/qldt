from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.shortcuts import render, get_object_or_404
from django.views import View
from .models import Department, SubjectGroup, Curriculum, Course, Subject, CurriculumSubject, SubjectType, SemesterAllocation, Major, ImportHistory
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
                    
                    print(f"Updating field: {field}, value: {value}")  # Debug log
                    
                    # Xử lý các trường học kỳ (HK1-HK6)
                    if field and field.startswith('hk'):
                        semester = int(field.replace('hk', ''))
                        
                        # Xử lý giá trị học kỳ
                        if value == '' or value is None:
                            # Xóa phân bố học kỳ nếu tồn tại
                            SemesterAllocation.objects.filter(
                                subject=subject, 
                                semester=semester
                            ).delete()
                        else:
                            # Cập nhật hoặc tạo mới phân bố học kỳ
                            try:
                                credits_value = float(value)
                                SemesterAllocation.objects.update_or_create(
                                    subject=subject,
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
                            subject.department = department
                        else:
                            subject.department = None
                        subject.save()
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
                    elif hasattr(subject, field):
                        # Xử lý kiểu dữ liệu
                        if field in ['credits']:
                            try:
                                value = float(value) if value else 0
                            except (ValueError, TypeError):
                                return JsonResponse({
                                    'status': 'error', 
                                    'message': f'Giá trị {field} không hợp lệ: {value}'
                                })
                        elif field in ['total_hours', 'theory_hours', 'practice_hours', 'exam_hours', 'order_number']:
                            try:
                                value = int(value) if value else 0
                            except (ValueError, TypeError):
                                return JsonResponse({
                                    'status': 'error', 
                                    'message': f'Giá trị {field} không hợp lệ: {value}'
                                })
                        
                        setattr(subject, field, value)
                        subject.save()
                        
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
                    subject = Subject.objects.get(id=id)
                    subject_name = subject.name
                    subject.delete()
                    
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
                    'message': 'Môn học không tồn tại'
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
                    'Tin học văn phòng'
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
                    'Khoa các BMC',
                    'Khoa các BMC', 
                    'Khoa các BMC',
                    'Khoa các BMC',
                    'Tổ Tin học',
                    'Khoa Ngoại ngữ',
                    'Khoa các BMC',
                    'Khoa KT-KT'
                ],
                'Loại môn': [
                    'Bắt buộc', 'Bắt buộc', 'Bắt buộc', 
                    'Bắt buộc', 'Bắt buộc', 'Bắt buộc',
                    'Bắt buộc', 'Bắt buộc'
                ],
                'Tổ bộ môn': [
                    'BM Lý luận chính trị', 'BM Lý luận chính trị', 'BM GD Thể chất & GD Quốc phòng và An ninh',
                    'BM GD Thể chất & GD Quốc phòng và An ninh', 'BM Công nghệ thông tin', 'BM Tiếng Anh', 
                    'BM Tâm lý học và Giáo dục học', 'BM Công nghệ thông tin'
                ],
                'Điều kiện tiên quyết': ['', '', '', '', '', '', '', ''],
                'Chuẩn đầu ra': ['', '', '', '', '', '', '', ''],
                'Mô tả môn học': ['', '', '', '', '', '', '', ''],
            }
            
            df = pd.DataFrame(sample_data)
            
            # Tạo file trong memory
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Chương trình đào tạo')
            
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
                
                if not curriculum_id:
                    return JsonResponse({'status': 'error', 'message': 'Vui lòng chọn chương trình đào tạo'})
                
                # Kiểm tra định dạng file
                if not excel_file.name.endswith(('.xlsx', '.xls')):
                    return JsonResponse({'status': 'error', 'message': 'File phải có định dạng Excel (.xlsx hoặc .xls)'})
                
                # Kiểm tra kích thước file (tối đa 10MB)
                if excel_file.size > 10 * 1024 * 1024:
                    return JsonResponse({'status': 'error', 'message': 'File không được vượt quá 10MB'})
                
                try:
                    # Đọc file Excel
                    df = pd.read_excel(excel_file)
                    print(f"File imported successfully, shape: {df.shape}")
                    
                except Exception as e:
                    return JsonResponse({'status': 'error', 'message': f'Không thể đọc file Excel: {str(e)}'})
                
                # Xử lý dữ liệu và lưu vào database - TRUYỀN excel_file VÀO
                result = self.process_excel_data(df, curriculum_id, request.user, excel_file)
                
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
            print(f"Error in import: {str(e)}")
            return JsonResponse({'status': 'error', 'message': f'Lỗi khi xử lý file: {str(e)}'})
    
    def process_excel_data(self, df, curriculum_id, user, excel_file):  # THÊM excel_file VÀO THAM SỐ
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
                    ma_mon_hoc = str(row.get('Mã môn học')).strip()
                    ten_mon_hoc = str(row.get('Tên học phần')).strip()
                    
                    if not ma_mon_hoc or not ten_mon_hoc:
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
                    
                    # Lấy hoặc tạo department
                    department_name = str(row.get('Đơn vị', '')).strip()
                    department = None
                    if department_name and department_name not in ['', 'nan']:
                        department, _ = Department.objects.get_or_create(
                            name=department_name,
                            defaults={
                                'code': department_name[:10].upper().replace(' ', ''),
                                'name': department_name
                            }
                        )
                    
                    # Lấy hoặc tạo subject_type
                    subject_type_name = str(row.get('Loại môn', 'Bắt buộc')).strip()
                    if not subject_type_name or subject_type_name == 'nan':
                        subject_type_name = 'Bắt buộc'
                    
                    subject_type, _ = SubjectType.objects.get_or_create(
                        name=subject_type_name,
                        defaults={
                            'code': subject_type_name[:10].upper().replace(' ', ''),
                            'name': subject_type_name
                        }
                    )
                    
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
                    
                    # Tạo hoặc cập nhật subject
                    subject, created = Subject.objects.update_or_create(
                        curriculum=curriculum,
                        code=ma_mon_hoc,
                        defaults={
                            'name': ten_mon_hoc,
                            'credits': so_tin_chi,
                            'total_hours': tong_so_gio,
                            'theory_hours': ly_thuyet,
                            'practice_hours': thuc_hanh,
                            'exam_hours': kiem_tra_thi,
                            'department': department,
                            'subject_type': subject_type,
                            'subject_group': subject_group,
                            'order_number': order_number
                        }
                    )
                    
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
                                        subject=subject,
                                        semester=hk,
                                        defaults={'credits': credit_value}
                                    )
                                    
                                    Subject.objects.update_or_create(
                                        curriculum=curriculum,
                                        code=ma_mon_hoc,
                                        semester=hk,
                                    )
                                except (ValueError, TypeError) as e:
                                    errors.append(f"Dòng {index + 2} - HK{hk}: Giá trị tín chỉ không hợp lệ: {credits_value}")
                    
                    processed_data.append({
                        'ma_mon_hoc': subject.code,
                        'ten_mon_hoc': subject.name,
                        'so_tin_chi': float(subject.credits),
                        'tong_so_gio': subject.total_hours,
                    })
                    
                except Exception as e:
                    error_msg = f"Dòng {index + 2}: {str(e)}"
                    errors.append(error_msg)
                    print(f"Error processing row {index + 2}: {str(e)}")
            
            # Lưu lịch sử import - SỬ DỤNG excel_file ĐÃ ĐƯỢC TRUYỀN VÀO
            ImportHistory.objects.create(
                curriculum=curriculum,
                file_name=excel_file.name,  # BÂY GIỜ excel_file ĐÃ ĐƯỢC XÁC ĐỊNH
                file_size=excel_file.size,   # BÂY GIỜ excel_file ĐÃ ĐƯỢC XÁC ĐỊNH
                imported_by=user,
                record_count=len(processed_data),
                status='success' if not errors else 'partial',
                errors=errors if errors else None
            )
            
            # Cập nhật tổng số tín chỉ cho curriculum
            curriculum.update_totals()
            
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
            print(f"Error in process_excel_data: {str(e)}")
            return {'status': 'error', 'message': f'Lỗi xử lý dữ liệu: {str(e)}'}
            
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
    
    subjects = Subject.objects.all()
    
    if curriculum_id:
        curriculum_subjects = CurriculumSubject.objects.filter(curriculum_id=curriculum_id)
        subject_ids = curriculum_subjects.values_list('subject_id', flat=True)
        subjects = subjects.filter(id__in=subject_ids)
    if department_id:
        subjects = subjects.filter(department_id=department_id)
    if subject_group_id:
        subjects = subjects.filter(subject_group_id=subject_group_id)
    
    # Sắp xếp theo loại môn và thứ tự
    subjects = subjects.order_by('code')
    
    subject_data = []
    for subject in subjects:
        # Lấy thông tin từ CurriculumSubject nếu có curriculum_id
        curriculum_info = {}
        if curriculum_id:
            try:
                cs = CurriculumSubject.objects.get(curriculum_id=curriculum_id, subject=subject)
                curriculum_info = {
                    'credits': float(cs.credits),
                    'total_hours': cs.total_hours,
                    'theory_hours': cs.theory_hours,
                    'practice_hours': cs.practice_hours,
                    'exam_hours': cs.exam_hours,
                    'order_number': cs.order_number,
                    'semester': cs.semester
                }
            except CurriculumSubject.DoesNotExist:
                curriculum_info = {}
        
        # Lấy phân bố học kỳ
        semester_allocations = SemesterAllocation.objects.filter(
            curriculum_subject__curriculum_id=curriculum_id,
            curriculum_subject__subject=subject
        ) if curriculum_id else SemesterAllocation.objects.none()
        
        semester_data = {f'hk{alloc.semester}': float(alloc.credits) for alloc in semester_allocations}
        
        subject_data.append({
            'id': subject.id,
            'ma_mon_hoc': subject.code,
            'ten_mon_hoc': subject.name,
            'so_tin_chi': curriculum_info.get('credits', 0),
            'tong_so_gio': curriculum_info.get('total_hours', 0),
            'ly_thuyet': curriculum_info.get('theory_hours', 0),
            'thuc_hanh': curriculum_info.get('practice_hours', 0),
            'kiem_tra_thi': curriculum_info.get('exam_hours', 0),
            'hk1': semester_data.get('hk1', ''),
            'hk2': semester_data.get('hk2', ''),
            'hk3': semester_data.get('hk3', ''),
            'hk4': semester_data.get('hk4', ''),
            'hk5': semester_data.get('hk5', ''),
            'hk6': semester_data.get('hk6', ''),
            'don_vi': subject.department.name if subject.department else '',
            'giang_vien': '',
            'loai_mon': subject.subject_type.name if subject.subject_type else '',
            'curriculum_id': curriculum_id,
            'is_existing': bool(curriculum_info)  # Đánh dấu đã có trong chương trình
        })
    
    return JsonResponse(subject_data, safe=False)

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
            
            # Kiểm tra mã môn học không trùng
            if Subject.objects.filter(curriculum=curriculum, code=data['code']).exists():
                return JsonResponse({
                    'status': 'error', 
                    'message': f'Mã môn học {data["code"]} đã tồn tại trong chương trình này'
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
            
            # Tạo môn học
            subject = Subject.objects.create(
                curriculum=curriculum,
                code=data['code'],
                name=data['name'],
                credits=float(data['credits']),
                total_hours=int(data.get('total_hours', 0) or 0),
                theory_hours=int(data.get('theory_hours', 0) or 0),
                practice_hours=int(data.get('practice_hours', 0) or 0),
                exam_hours=int(data.get('exam_hours', 0) or 0),
                semester=int(data.get('semester', 0) or None),
                is_elective=bool(data.get('is_elective', False)),
                elective_group=data.get('elective_group', ''),
                department=department,
                subject_group=subject_group,
                subject_type=subject_type,
                prerequisites=data.get('prerequisites', ''),
                learning_outcomes=data.get('learning_outcomes', ''),
                description=data.get('description', ''),
                order_number=int(data.get('order_number', 0) or 0)
            )
            
            # Tạo phân bố học kỳ
            semester_allocations = data.get('semester_allocations', {})
            for semester_str, credits_value in semester_allocations.items():
                semester = int(semester_str.replace('hk', ''))
                if credits_value and float(credits_value) > 0:
                    SemesterAllocation.objects.create(
                        subject=subject,
                        semester=semester,
                        credits=float(credits_value)
                    )
            
            return JsonResponse({
                'status': 'success',
                'message': 'Đã tạo môn học thành công',
                'id': subject.id
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
            
            # Kiểm tra mã môn học không trùng
            if Subject.objects.filter(curriculum=curriculum, code=data['code']).exists():
                return JsonResponse({
                    'status': 'error', 
                    'message': f'Mã môn học {data["code"]} đã tồn tại trong chương trình này'
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
            
            # Tạo môn học
            subject = Subject.objects.create(
                curriculum=curriculum,
                code=data['code'],
                name=data['name'],
                credits=float(data['credits']),
                total_hours=int(data.get('total_hours', 0) or 0),
                theory_hours=int(data.get('theory_hours', 0) or 0),
                practice_hours=int(data.get('practice_hours', 0) or 0),
                exam_hours=int(data.get('exam_hours', 0) or 0),
                semester=int(data.get('semester', 0) or None),
                is_elective=bool(data.get('is_elective', False)),
                elective_group=data.get('elective_group', ''),
                department=department,
                subject_group=subject_group,
                subject_type=subject_type,
                prerequisites=data.get('prerequisites', ''),
                learning_outcomes=data.get('learning_outcomes', ''),
                description=data.get('description', ''),
                order_number=int(data.get('order_number', 0) or 0)
            )
            
            # Tạo phân bố học kỳ
            semester_allocations = data.get('semester_allocations', {})
            for semester_str, credits_value in semester_allocations.items():
                semester = int(semester_str.replace('hk', ''))
                if credits_value and float(credits_value) > 0:
                    SemesterAllocation.objects.create(
                        subject=subject,
                        semester=semester,
                        credits=float(credits_value)
                    )
            
            return JsonResponse({
                'status': 'success',
                'message': 'Đã tạo môn học thành công',
                'id': subject.id
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
