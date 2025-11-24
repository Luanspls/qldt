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
                    elif field == 'course':
                        # Cập nhật khóa học cho curriculum_subject
                        curriculum_subject = Subject.objects.get(id=id)
                        try:
                            if value and value.strip():
                                course = Course.objects.get(id=int(value)) 
                                    # defaults={'code': value.strip()[:10].upper().replace(' ', '')}
                                curriculum_subject.course = course
                                curriculum_subject.save()
                            else:
                                curriculum_subject.course = None
                                curriculum_subject.save()
                            return JsonResponse({
                                'status': 'success', 
                                'message': 'Đã cập nhật khóa học thành công'
                            })
                        except Course.DoesNotExist:
                            return JsonResponse({
                                'status': 'error', 
                                'message': f'Khóa học không tồn tại với id: {value}'
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
                    'course_id': cs.course.id if cs.course else '',
                    'course_code': cs.course.code if cs.course else '',
                    'course_name': cs.course.name if cs.course else '',
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
                    'Môn học chung', 'Môn học chung', 'Môn học chung', 
                    'Môn học bắt buộc', 'Môn học chung', 'Môn học chung',
                    'Môn học cơ sở', 'Môn học chuyên ngành'
                ],
                'Tổ bộ môn': [
                    'Bộ môn Lý luận chính trị', 'Bộ môn Lý luận chính trị', 'Bộ môn GD Thể chất & GD Quốc phòng và An ninh',
                    'Bộ môn GD Thể chất & GD Quốc phòng và An ninh', 'Bộ môn Công nghệ thông tin', 'Bộ môn Tiếng Anh', 
                    'Bộ môn Tâm lý học và Giáo dục học', 'Bộ môn Kinh tế'
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
                course_id = request.POST.get('course_id')
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
                result = self.process_excel_data(df, curriculum_id, course_id, request.user, excel_file, sheet_name)
                
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
    
    def process_excel_data(self, df, curriculum_id, course_id, user, excel_file, sheet_name):  # THÊM excel_file, sheet_name VÀO THAM SỐ
        """Xử lý dữ liệu từ Excel và lưu vào database"""
        try:
            curriculum = Curriculum.objects.get(id=curriculum_id)
            course = Course.objects.get(id=course_id)
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
                    curriculum_prefix = curriculum.code.replace(' ', '_').upper()[:15]
                    base_code = original_code
                    
                    # Kiểm tra xem mã đã tồn tại chưa
                    proposed_code = f"{curriculum_prefix}_{base_code}"
                    counter = 1
                    unique_code = proposed_code
                    
                    while Subject.objects.filter(code=unique_code).exists():
                        # Kiểm tra xem có phải là cùng một môn học không (dựa trên tên và các thuộc tính)
                        existing_subject = Subject.objects.get(code=unique_code)
                        
                        if (existing_subject.name == ten_mon_hoc and
                            existing_subject.curriculum.id == curriculum.id and
                            existing_subject.course.id == course.id and
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
                        course = course,
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
                            'original_code': original_code,
                            
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
            'curriculum_id': cc.curriculum.id,
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
    instructors = Instructor.objects.select_related('department', 'subject_group')
     # Áp dụng bộ lọc nếu có
    department_id = request.GET.get('department_id')
    if department_id:
        instructors = instructors.filter(department_id=department_id)
    
    subject_group_id = request.GET.get('subject_group_id')
    if subject_group_id:
        instructors = instructors.filter(subject_group_id=subject_group_id)
    
    is_active = request.GET.get('is_active')
    if is_active is not None:
        # Chuyển đổi từ string sang boolean
        is_active_bool = is_active.lower() == 'true'
        instructors = instructors.filter(is_active=is_active_bool)
    instructors_data = instructors.values('id', 'code', 'full_name', 'email', 'phone', 'department_id', 'subject_group_id', 'is_active')
    return JsonResponse(list(instructors_data), safe=False)

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

@csrf_exempt
def api_create_instructor(request):
    """API tạo giảng viên mới"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Kiểm tra các trường bắt buộc
            required_fields = ['code', 'full_name']
            for field in required_fields:
                if not data.get(field):
                    return JsonResponse({
                        'status': 'error', 
                        'message': f'Thiếu trường bắt buộc: {field}'
                    })
            
            # Xử lý department
            department = None
            if data.get('department_id'):
                try:
                    department = Department.objects.get(id=data['department_id'])
                except Department.DoesNotExist:
                    pass
            
            # Xử lý subject_group
            subject_group = None
            if data.get('subject_group_id'):
                try:
                    subject_group = SubjectGroup.objects.get(id=data['subject_group_id'])
                except SubjectGroup.DoesNotExist:
                    pass
            
            # Tạo giảng viên
            instructor = Instructor.objects.create(
                code=data['code'],
                full_name=data['full_name'],
                email=data.get('email'),
                phone=data.get('phone'),
                department=department,
                subject_group=subject_group,
                is_active=data.get('is_active', True)
            )
            
            return JsonResponse({
                'status': 'success',
                'message': 'Đã tạo giảng viên thành công',
                'id': instructor.id
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error', 
                'message': f'Lỗi khi tạo giảng viên: {str(e)}'
            })
    
    return JsonResponse({
        'status': 'error', 
        'message': 'Method not allowed'
    })

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
    def get(self, request, object_type):
        """Tải file Excel mẫu cho từng loại đối tượng với sheet hướng dẫn"""
        try:
            # Tạo workbook
            output = io.BytesIO()
                
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
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
                
                elif object_type == 'instructor':
                    sample_data = self.get_instructor_template()
                    filename = "mau_import_giang_vien.xlsx"
                    df = pd.DataFrame(sample_data)
                    df.to_excel(writer, index=False, sheet_name='Dữ liệu mẫu')
                        
                    # Tạo sheet hướng dẫn cho giảng viên
                    self.create_instructor_guide_sheet(writer)
                        
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
        """Tạo sheet hướng dẫn cho import lớp học - SỬA CHO XLSXWRITER"""
        try:
            # Lấy workbook và worksheet từ writer
            workbook = writer.book
            worksheet = workbook.add_worksheet('Hướng dẫn nhập liệu')
            
            # Định dạng
            bold_format = workbook.add_format({'bold': True})
            header_format = workbook.add_format({'bold': True, 'bg_color': '#DDEBF7'})
            
            # Lấy danh sách chương trình
            curricula = Curriculum.objects.all().values('code', 'name', 'academic_year')
            # Lấy danh sách khóa học
            courses = Course.objects.all().values('code', 'name', 'curriculum__code')
            # Lấy danh sách lớp học hiện có
            classes = Class.objects.all().values('code', 'name', 'curriculum__code', 'course__code')
            
            row = 0
            
            # Section Chương trình đào tạo
            worksheet.write(row, 0, "DANH SÁCH CHƯƠNG TRÌNH ĐÀO TẠO CÓ SẴN", bold_format)
            row += 1
            worksheet.write(row, 0, "Mã chương trình", header_format)
            worksheet.write(row, 1, "Tên chương trình", header_format)
            worksheet.write(row, 2, "Năm học", header_format)
            row += 1
            
            for curriculum in curricula:
                worksheet.write(row, 0, curriculum['code'])
                worksheet.write(row, 1, curriculum['name'])
                worksheet.write(row, 2, curriculum['academic_year'])
                row += 1
                
            row += 2
            
            # Section Khóa học
            worksheet.write(row, 0, "DANH SÁCH KHÓA HỌC CÓ SẴN", bold_format)
            row += 1
            worksheet.write(row, 0, "Mã khóa học", header_format)
            worksheet.write(row, 1, "Tên khóa học", header_format)
            worksheet.write(row, 2, "Mã chương trình", header_format)
            row += 1
            
            for course in courses:
                worksheet.write(row, 0, course['code'])
                worksheet.write(row, 1, course['name'])
                worksheet.write(row, 2, course['curriculum__code'])
                row += 1
                
            row += 2
            
            # Section Lớp học hiện có
            worksheet.write(row, 0, "DANH SÁCH LỚP HỌC HIỆN CÓ", bold_format)
            row += 1
            worksheet.write(row, 0, "Mã lớp", header_format)
            worksheet.write(row, 1, "Tên lớp", header_format)
            worksheet.write(row, 2, "Mã chương trình", header_format)
            worksheet.write(row, 3, "Mã khóa học", header_format)
            row += 1
            
            for class_item in classes:
                worksheet.write(row, 0, class_item['code'])
                worksheet.write(row, 1, class_item['name'])
                worksheet.write(row, 2, class_item['curriculum__code'])
                worksheet.write(row, 3, class_item['course__code'])
                row += 1
                
            row += 2
            
            # Thêm ghi chú
            worksheet.write(row, 0, "LƯU Ý QUAN TRỌNG:", bold_format)
            row += 1
            
            notes = [
                "1. Chỉ nhập dữ liệu vào sheet 'Dữ liệu mẫu'",
                "2. Các cột có dấu * là bắt buộc",
                "3. Sử dụng các giá trị từ danh sách trên để đảm bảo tính nhất quán",
                "4. Mã lớp không được trùng với các lớp đã có trong hệ thống",
                "5. Ngày tháng nhập theo định dạng YYYY-MM-DD (ví dụ: 2023-09-01)"
            ]
            
            for note in notes:
                worksheet.write(row, 0, note)
                row += 1
                
        except Exception as e:
            print(f"Error creating guide sheet: {str(e)}")

    def create_combined_class_guide_sheet(self, writer):
        """Tạo sheet hướng dẫn cho import lớp học ghép - SỬA CHO XLSXWRITER"""
        try:
            workbook = writer.book
            worksheet = workbook.add_worksheet('Hướng dẫn nhập liệu')
            
            bold_format = workbook.add_format({'bold': True})
            header_format = workbook.add_format({'bold': True, 'bg_color': '#E2EFDA'})
            
            # Lấy dữ liệu
            curricula = Curriculum.objects.all().values('code', 'name', 'academic_year')
            classes = Class.objects.filter(is_combined=False).values('code', 'name', 'curriculum__code')
            combined_classes = CombinedClass.objects.all().values('code', 'name', 'curriculum__code')
            
            row = 0
            
            # Section Chương trình đào tạo
            worksheet.write(row, 0, "DANH SÁCH CHƯƠNG TRÌNH ĐÀO TẠO CÓ SẴN", bold_format)
            row += 1
            worksheet.write(row, 0, "Mã chương trình", header_format)
            worksheet.write(row, 1, "Tên chương trình", header_format)
            worksheet.write(row, 2, "Năm học", header_format)
            row += 1
            
            for curriculum in curricula:
                worksheet.write(row, 0, curriculum['code'])
                worksheet.write(row, 1, curriculum['name'])
                worksheet.write(row, 2, curriculum['academic_year'])
                row += 1
                
            row += 2
            
            # Section Lớp học có thể ghép
            worksheet.write(row, 0, "DANH SÁCH LỚP HỌC CÓ THỂ GHÉP", bold_format)
            row += 1
            worksheet.write(row, 0, "Mã lớp", header_format)
            worksheet.write(row, 1, "Tên lớp", header_format)
            worksheet.write(row, 2, "Mã chương trình", header_format)
            row += 1
            
            for class_item in classes:
                worksheet.write(row, 0, class_item['code'])
                worksheet.write(row, 1, class_item['name'])
                worksheet.write(row, 2, class_item['curriculum__code'])
                row += 1
                
            row += 2
            
            # Thêm ghi chú
            worksheet.write(row, 0, "LƯU Ý QUAN TRỌNG:", bold_format)
            row += 1
            
            notes = [
                "1. Chỉ nhập dữ liệu vào sheet 'Dữ liệu mẫu'",
                "2. Các cột có dấu * là bắt buộc",
                "3. Sử dụng các giá trị từ danh sách trên để đảm bảo tính nhất quán",
                "4. Mã lớp ghép không được trùng với các lớp ghép đã có",
                "5. Các mã lớp thành phần phân cách bằng dấu phẩy (ví dụ: DHTI001,DHTI002)",
                "6. Các lớp thành phần phải thuộc cùng chương trình đào tạo"
            ]
            
            for note in notes:
                worksheet.write(row, 0, note)
                row += 1
                
        except Exception as e:
            print(f"Error creating combined class guide sheet: {str(e)}")

    def create_instructor_guide_sheet(self, writer):
        """Tạo sheet hướng dẫn cho import giảng viên"""
        try:
            workbook = writer.book
            worksheet = workbook.add_worksheet('Hướng dẫn nhập liệu')
            
            bold_format = workbook.add_format({'bold': True})
            header_format = workbook.add_format({'bold': True, 'bg_color': '#DDEBF7'})
            
            # Lấy dữ liệu từ database
            departments = Department.objects.all().values('code', 'name')
            subject_groups = SubjectGroup.objects.all().values('code', 'name', 'department__code')
            
            row = 0
            
            # Section Khoa
            worksheet.write(row, 0, "DANH SÁCH KHOA CÓ SẴN", bold_format)
            row += 1
            worksheet.write(row, 0, "Mã khoa", header_format)
            worksheet.write(row, 1, "Tên khoa", header_format)
            row += 1
            
            for department in departments:
                worksheet.write(row, 0, department['code'])
                worksheet.write(row, 1, department['name'])
                row += 1
                
            row += 2
            
            # Section Tổ bộ môn
            worksheet.write(row, 0, "DANH SÁCH TỔ BỘ MÔN CÓ SẴN", bold_format)
            row += 1
            worksheet.write(row, 0, "Mã tổ bộ môn", header_format)
            worksheet.write(row, 1, "Tên tổ bộ môn", header_format)
            worksheet.write(row, 2, "Mã khoa", header_format)
            row += 1
            
            for subject_group in subject_groups:
                worksheet.write(row, 0, subject_group['code'])
                worksheet.write(row, 1, subject_group['name'])
                worksheet.write(row, 2, subject_group['department__code'] or '')
                row += 1
                
            row += 2
            
            # Thêm ghi chú
            worksheet.write(row, 0, "LƯU Ý QUAN TRỌNG:", bold_format)
            row += 1
            
            notes = [
                "1. Chỉ nhập dữ liệu vào sheet 'Dữ liệu mẫu'",
                "2. Các cột có dấu * là bắt buộc",
                "3. Sử dụng các giá trị từ danh sách trên để đảm bảo tính nhất quán",
                "4. Mã giảng viên không được trùng",
                "5. Trạng thái: 'Đang hoạt động' hoặc 'Ngừng hoạt động'",
                "6. Mã khoa và mã tổ bộ môn phải tồn tại trong hệ thống (nếu có)"
            ]
            
            for note in notes:
                worksheet.write(row, 0, note)
                row += 1
                
        except Exception as e:
            print(f"Error creating instructor guide sheet: {str(e)}")
    
    def create_teaching_assignment_guide_sheet(self, writer):
        """Tạo sheet hướng dẫn cho import phân công giảng dạy - SỬA CHO XLSXWRITER"""
        try:
            workbook = writer.book
            worksheet = workbook.add_worksheet('Hướng dẫn nhập liệu')
            
            bold_format = workbook.add_format({'bold': True})
            header_format = workbook.add_format({'bold': True, 'bg_color': '#FCE4D6'})
            
            # Lấy dữ liệu
            instructors = Instructor.objects.all().values('code', 'full_name', 'department__name')
            curriculum_subjects = Subject.objects.select_related('curriculum').all()
            classes = Class.objects.all().values('code', 'name', 'curriculum__code')
            combined_classes = CombinedClass.objects.all().values('code', 'name', 'curriculum__code')
            
            row = 0
            
            # Section Giảng viên
            worksheet.write(row, 0, "DANH SÁCH GIẢNG VIÊN", bold_format)
            row += 1
            worksheet.write(row, 0, "Mã giảng viên", header_format)
            worksheet.write(row, 1, "Họ tên", header_format)
            worksheet.write(row, 2, "Khoa", header_format)
            row += 1
            
            for instructor in instructors:
                worksheet.write(row, 0, instructor['code'])
                worksheet.write(row, 1, instructor['full_name'])
                worksheet.write(row, 2, instructor['department__name'] or '')
                row += 1
                
            row += 2
            
            # Section Môn học
            worksheet.write(row, 0, "DANH SÁCH MÔN HỌC", bold_format)
            row += 1
            worksheet.write(row, 0, "Mã môn học", header_format)
            worksheet.write(row, 1, "Tên môn học", header_format)
            worksheet.write(row, 2, "Mã chương trình", header_format)
            row += 1
            
            for subject in curriculum_subjects:
                worksheet.write(row, 0, subject.code)
                worksheet.write(row, 1, subject.name)
                worksheet.write(row, 2, subject.curriculum.code if subject.curriculum else '')
                row += 1
                
            row += 2
            
            # Thêm ghi chú
            worksheet.write(row, 0, "LƯU Ý QUAN TRỌNG:", bold_format)
            row += 1
            
            notes = [
                "1. Chỉ nhập dữ liệu vào sheet 'Dữ liệu mẫu'",
                "2. Các cột có dấu * là bắt buộc",
                "3. Sử dụng các giá trị từ danh sách trên để đảm bảo tính nhất quán",
                "4. Loại lớp phải là 'Thường' hoặc 'Ghép'",
                "5. Học kỳ phải là số từ 1 đến 12",
                "6. Năm học theo định dạng YYYY-YYYY (ví dụ: 2023-2024)",
                "7. Là giảng viên chính: 'Có' hoặc 'Không'"
            ]
            
            for note in notes:
                worksheet.write(row, 0, note)
                row += 1
                
        except Exception as e:
            print(f"Error creating teaching assignment guide sheet: {str(e)}")
        
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
                elif object_type == 'instructor':
                    result = self.process_instructor_import(df, request.user, excel_file, selected_sheet)
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
    
    def get_instructor_template(self):
        """Tạo template cho import giảng viên"""
        return {
            'Mã giảng viên*': ['GV001', 'GV002', 'GV003'],
            'Họ và tên*': ['Nguyễn Văn A', 'Trần Thị B', 'Lê Văn C'],
            'Email': ['nva@example.com', 'ttb@example.com', 'lvc@example.com'],
            'Số điện thoại': ['0123456789', '0987654321', '0912345678'],
            'Mã khoa': ['KHOA_CNTT', 'KHOA_CNTT', 'KHOA_KT'],
            'Mã tổ bộ môn': ['BM_HTTT', 'BM_MMT', 'BM_QTKD'],
            'Trạng thái': ['Đang hoạt động', 'Đang hoạt động', 'Ngừng hoạt động']
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
    
    def process_instructor_import(self, df, user, excel_file, sheet_name):
        """Xử lý import giảng viên"""
        try:
            created_count = 0
            updated_count = 0
            errors = []
            processed_data = []
                
            # Kiểm tra cấu trúc file
            required_columns = ['Mã giảng viên*', 'Họ và tên*']
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
                    code = str(row.get('Mã giảng viên*')).strip()
                    full_name = str(row.get('Họ và tên*')).strip()
                        
                    if not code or not full_name:
                        errors.append(f"Dòng {index + 2}: Thiếu thông tin bắt buộc")
                        continue

                    # Xử lý email
                    email = str(row.get('Email', '')).strip()
                    if email in ['', 'nan']:
                        email = None

                    # Xử lý số điện thoại
                    phone = str(row.get('Số điện thoại', '')).strip()
                    if phone in ['', 'nan']:
                        phone = None

                    # Xử lý khoa
                    department_code = str(row.get('Mã khoa', '')).strip()
                    department = None
                    if department_code and department_code not in ['', 'nan']:
                        try:
                            department = Department.objects.get(code=department_code)
                        except Department.DoesNotExist:
                            errors.append(f"Dòng {index + 2}: Không tìm thấy khoa với mã '{department_code}'")
                            continue

                    # Xử lý tổ bộ môn
                    subject_group_code = str(row.get('Mã tổ bộ môn', '')).strip()
                    subject_group = None
                    if subject_group_code and subject_group_code not in ['', 'nan']:
                        try:
                            subject_group = SubjectGroup.objects.get(code=subject_group_code)
                        except SubjectGroup.DoesNotExist:
                            errors.append(f"Dòng {index + 2}: Không tìm thấy tổ bộ môn với mã '{subject_group_code}'")
                            continue

                    # Xử lý trạng thái
                    status_str = str(row.get('Trạng thái', 'Đang hoạt động')).strip()
                    is_active = status_str.lower() in ['đang hoạt động', 'active', 'true', '1', 'có', 'yes']

                    # Tạo hoặc cập nhật giảng viên
                    instructor, created = Instructor.objects.update_or_create(
                        code=code,
                        defaults={
                            'full_name': full_name,
                            'email': email,
                            'phone': phone,
                            'department': department,
                            'subject_group': subject_group,
                            'is_active': is_active
                        }
                    )
                        
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
                        
                    processed_data.append({
                        'code': instructor.code,
                        'full_name': instructor.full_name,
                        'email': instructor.email,
                        'department': department.name if department else 'N/A'
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
                'message': f'Import thành công: {created_count} giảng viên được tạo, {updated_count} giảng viên được cập nhật',
                'created_count': created_count,
                'updated_count': updated_count,
                'processed_data': processed_data,
                'errors': errors
            }
                
        except Exception as e:
            print(f"Error in process_instructor_import: {str(e)}")
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

@csrf_exempt
def api_class_detail(request, id):
    """API lấy thông tin chi tiết lớp học"""
    if request.method == 'GET':
        try:
            class_obj = Class.objects.get(id=id)
            
            class_data = {
                'id': class_obj.id,
                'code': class_obj.code,
                'name': class_obj.name,
                'curriculum_id': class_obj.curriculum.id if class_obj.curriculum else None,
                'course_id': class_obj.course.id if class_obj.course else None,
                'start_date': class_obj.start_date,
                'end_date': class_obj.end_date,
                'is_combined': class_obj.is_combined,
                'combined_class_code': class_obj.combined_class_code,
                'description': class_obj.description
            }
            return JsonResponse({'status': 'success', 'data': class_data})
        except Class.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Lớp học không tồn tại'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

@csrf_exempt
def api_update_class(request, id):
    """API cập nhật lớp học"""
    if request.method == 'PUT':
        try:
            class_obj = Class.objects.get(id=id)
            data = json.loads(request.body)
            
            # Cập nhật các trường
            if 'code' in data:
                class_obj.code = data['code']
            if 'name' in data:
                class_obj.name = data['name']
            if 'curriculum_id' in data:
                try:
                    class_obj.curriculum = Curriculum.objects.get(id=data['curriculum_id'])
                except Curriculum.DoesNotExist:
                    return JsonResponse({'status': 'error', 'message': 'Chương trình không tồn tại'})
            if 'course_id' in data:
                try:
                    class_obj.course = Course.objects.get(id=data['course_id'])
                except Course.DoesNotExist:
                    return JsonResponse({'status': 'error', 'message': 'Khóa học không tồn tại'})
            if 'start_date' in data:
                class_obj.start_date = data['start_date'] if data['start_date'] else None
            if 'end_date' in data:
                class_obj.end_date = data['end_date'] if data['end_date'] else None
            if 'is_combined' in data:
                class_obj.is_combined = data['is_combined']
            if 'combined_class_code' in data:
                class_obj.combined_class_code = data['combined_class_code'] if data['combined_class_code'] else None
            if 'description' in data:
                class_obj.description = data['description'] if data['description'] else None
            
            class_obj.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Đã cập nhật lớp học thành công'
            })
            
        except Class.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Lớp học không tồn tại'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

@csrf_exempt
def api_delete_class(request, id):
    """API xóa lớp học"""
    if request.method == 'DELETE':
        try:
            class_obj = Class.objects.get(id=id)
            class_name = class_obj.name
            class_obj.delete()
            
            return JsonResponse({
                'status': 'success',
                'message': f'Đã xóa lớp học {class_name} thành công'
            })
            
        except Class.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Lớp học không tồn tại'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

@csrf_exempt
def api_combined_class_detail(request, id):
    """API lấy thông tin chi tiết lớp học ghép"""
    if request.method == 'GET':
        try:
            combined_class = CombinedClass.objects.prefetch_related('classes').get(id=id)
            class_data = {
                'id': combined_class.id,
                'code': combined_class.code,
                'name': combined_class.name,
                'curriculum_id': combined_class.curriculum.id if combined_class.curriculum else None,
                'description': combined_class.description,
                'classes': [{'id': c.id, 'code': c.code, 'name': c.name} for c in combined_class.classes.all()]
            }
            return JsonResponse({'status': 'success', 'data': class_data})
        except CombinedClass.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Lớp học ghép không tồn tại'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

@csrf_exempt
def api_update_combined_class(request, id):
    """API cập nhật lớp học ghép"""
    if request.method == 'PUT':
        try:
            combined_class = CombinedClass.objects.get(id=id)
            data = json.loads(request.body)
            
            # Cập nhật các trường
            if 'code' in data:
                combined_class.code = data['code']
            if 'name' in data:
                combined_class.name = data['name']
            if 'curriculum_id' in data:
                try:
                    combined_class.curriculum = Curriculum.objects.get(id=data['curriculum_id'])
                except Curriculum.DoesNotExist:
                    return JsonResponse({'status': 'error', 'message': 'Chương trình không tồn tại'})
            if 'description' in data:
                combined_class.description = data['description'] if data['description'] else None
            
            combined_class.save()
            
            # Cập nhật các lớp thành phần
            if 'classes' in data:
                classes = Class.objects.filter(id__in=data['classes'])
                combined_class.classes.set(classes)
            
            return JsonResponse({
                'status': 'success',
                'message': 'Đã cập nhật lớp học ghép thành công'
            })
            
        except CombinedClass.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Lớp học ghép không tồn tại'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

@csrf_exempt
def api_delete_combined_class(request, id):
    """API xóa lớp học ghép"""
    if request.method == 'DELETE':
        try:
            combined_class = CombinedClass.objects.get(id=id)
            class_name = combined_class.name
            combined_class.delete()
            
            return JsonResponse({
                'status': 'success',
                'message': f'Đã xóa lớp học ghép {class_name} thành công'
            })
            
        except CombinedClass.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Lớp học ghép không tồn tại'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

@csrf_exempt
def api_instructor_detail(request, id):
    """API lấy thông tin chi tiết giảng viên"""
    if request.method == 'GET':
        try:
            instructor = Instructor.objects.get(id=id)
            instructor_data = {
                'id': instructor.id,
                'code': instructor.code,
                'full_name': instructor.full_name,
                'email': instructor.email,
                'phone': instructor.phone,
                'department_id': instructor.department.id if instructor.department else None,
                'subject_group_id': instructor.subject_group.id if instructor.subject_group else None,
                'is_active': instructor.is_active
            }
            return JsonResponse({'status': 'success', 'data': instructor_data})
        except Instructor.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Giảng viên không tồn tại'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

@csrf_exempt
def api_update_instructor(request, id):
    """API cập nhật giảng viên"""
    if request.method == 'PUT':
        try:
            instructor = Instructor.objects.get(id=id)
            data = json.loads(request.body)
            
            # Cập nhật các trường
            if 'code' in data:
                instructor.code = data['code']
            if 'full_name' in data:
                instructor.full_name = data['full_name']
            if 'email' in data:
                instructor.email = data['email'] if data['email'] else None
            if 'phone' in data:
                instructor.phone = data['phone'] if data['phone'] else None
            if 'department_id' in data:
                try:
                    instructor.department = Department.objects.get(id=data['department_id'])
                except Department.DoesNotExist:
                    return JsonResponse({'status': 'error', 'message': 'Đơn vị Khoa không tồn tại'})
            if 'subject_group_id' in data:
                try:
                    instructor.subject_group = SubjectGroup.objects.get(id=data['subject_group_id'])
                except SubjectGroup.DoesNotExist:
                    return JsonResponse({'status': 'error', 'message': 'Bộ môn không tồn tại'})
            if 'is_active' in data:
                instructor.is_active = data['is_active']
            
            instructor.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Đã cập nhật giảng viên thành công'
            })
            
        except Instructor.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Giảng viên không tồn tại'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

@csrf_exempt
def api_delete_instructor(request, id):
    """API xóa giảng viên"""
    if request.method == 'DELETE':
        try:
            instructor = Instructor.objects.get(id=id)
            instructor_name = instructor.full_name
            instructor.delete()
            
            return JsonResponse({
                'status': 'success',
                'message': f'Đã xóa giảng viên {instructor_name} thành công'
            })
            
        except Instructor.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Giảng viên không tồn tại'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

@csrf_exempt
def api_teaching_assignment_detail(request, id):
    """API lấy thông tin chi tiết phân công giảng dạy"""
    if request.method == 'GET':
        try:
            assignment = TeachingAssignment.objects.select_related(
                'instructor', 'curriculum_subject', 'class_obj', 'combined_class'
            ).get(id=id)
            
            assignment_data = {
                'id': assignment.id,
                'instructor_id': assignment.instructor.id,
                'curiculum_subject_id': assignment.curriculum_subject.id,
                'class_obj_id': assignment.class_obj.id if assignment.class_obj else None,
                'combined_class_id': assignment.combined_class.id if assignment.combined_class else None,
                'academic_year': assignment.academic_year,
                'semester': assignment.semester,
                'is_main_instructor': assignment.is_main_instructor,
                'student_count': assignment.student_count,
                'teaching_hours': assignment.teaching_hours
            }
            return JsonResponse({'status': 'success', 'data': assignment_data})
        except TeachingAssignment.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Phân công giảng dạy không tồn tại'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

@csrf_exempt
def api_update_teaching_assignment(request, id):
    """API cập nhật phân công giảng dạy"""
    if request.method == 'PUT':
        try:
            assignment = TeachingAssignment.objects.get(id=id)
            data = json.loads(request.body)
            
            # Cập nhật các trường
            if 'instructor_id' in data:
                try:
                    assignment.instructor = Instructor.objects.get(id=data['instructor_id'])
                except Instructor.DoesNotExist:
                    return JsonResponse({'status': 'error', 'message': 'Giảng viên không tồn tại'})
            if 'curriculum_subject_id' in data:
                try:
                    assignment.curriculum_subject = Subject.objects.get(id=data['curriculum_subject_id'])
                except Subject.DoesNotExist:
                    return JsonResponse({'status': 'error', 'message': 'Môn học không tồn tại'})
            if 'class_obj_id' in data:
                try:
                    assignment.class_obj = Class.objects.get(id=data['class_obj_id'])
                except Class.DoesNotExist:
                    return JsonResponse({'status': 'error', 'message': 'Lớp học không tồn tại'})
            if 'combined_class_id' in data:
                try:
                    assignment.combined_class = CombinedClass.objects.get(id=data['combined_class_id'])
                except CombinedClass.DoesNotExist:
                    return JsonResponse({'status': 'error', 'message': 'Lớp ghép không tồn tại'})
            if 'academic_year' in data:
                assignment.academic_year = data['academic_year']
            if 'semester' in data:
                assignment.semester = data['semester']
            if 'is_main_instructor' in data:
                assignment.is_main_instructor = data['is_main_instructor']
            if 'student_count' in data:
                assignment.student_count = data['student_count']
            if 'teaching_hours' in data:
                assignment.teaching_hours = data['teaching_hours']
            
            assignment.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Đã cập nhật phân công giảng dạy thành công'
            })
            
        except TeachingAssignment.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Phân công giảng dạy không tồn tại'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

@csrf_exempt
def api_delete_teaching_assignment(request, id):
    """API xóa phân công giảng dạy"""
    if request.method == 'DELETE':
        try:
            assignment = TeachingAssignment.objects.get(id=id)
            assignment.delete()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Đã xóa phân công giảng dạy thành công'
            })
            
        except TeachingAssignment.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Phân công giảng dạy không tồn tại'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
