# models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
import re

class Department(models.Model):
    code = models.CharField(max_length=20, unique=True, verbose_name="Mã khoa")
    name = models.CharField(max_length=255, verbose_name="Tên khoa")
    description = models.TextField(blank=True, null=True, verbose_name="Mô tả")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'departments'
        verbose_name = 'Khoa'
        verbose_name_plural = 'Các khoa'

    def __str__(self):
        return f"{self.code} - {self.name}"


class SubjectGroup(models.Model):
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, verbose_name="Khoa quản lý")
    code = models.CharField(max_length=20, unique=True, verbose_name="Mã tổ bộ môn")
    name = models.CharField(max_length=255, verbose_name="Tên tổ bộ môn")
    description = models.TextField(blank=True, null=True, verbose_name="Mô tả")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'subject_groups'
        verbose_name = 'Tổ bộ môn'
        verbose_name_plural = 'Các tổ bộ môn'

    def __str__(self):
        return f"{self.code} - {self.name}"


class Major(models.Model):
    code = models.CharField(max_length=20, unique=True, verbose_name="Mã ngành")
    name = models.CharField(max_length=255, verbose_name="Tên ngành")
    description = models.TextField(blank=True, null=True, verbose_name="Mô tả")
    duration_years = models.IntegerField(
        default=3, 
        validators=[MinValueValidator(1), MaxValueValidator(6)],
        verbose_name="Thời gian đào tạo (năm)"
    )
    total_credits = models.IntegerField(default=0, verbose_name="Tổng số tín chỉ")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'majors'
        verbose_name = 'Ngành đào tạo'
        verbose_name_plural = 'Các ngành đào tạo'

    def __str__(self):
        return f"{self.code} - {self.name}"


class Curriculum(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Bản nháp'),
        ('under_review', 'Chờ duyệt'),
        ('approved', 'Đã phê duyệt'),
        ('active', 'Đang áp dụng'),
        ('archived', 'Lưu trữ'),
    ]

    major = models.ForeignKey(Major, on_delete=models.CASCADE, verbose_name="Ngành đào tạo", db_column="major_id")
    code = models.CharField(max_length=50, unique=True, verbose_name="Mã chương trình")
    name = models.CharField(max_length=255, verbose_name="Tên chương trình")
    academic_year = models.CharField(max_length=20, verbose_name="Năm học áp dụng")
    description = models.TextField(blank=True, null=True, verbose_name="Mô tả")
    total_credits = models.IntegerField(default=0, verbose_name="Tổng số tín chỉ")
    total_hours = models.IntegerField(default=0, verbose_name="Tổng số giờ")
    theory_hours = models.IntegerField(default=0, verbose_name="Số giờ lý thuyết")
    practice_hours = models.IntegerField(default=0, verbose_name="Số giờ thực hành")
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='draft',
        verbose_name="Trạng thái"
    )
    version = models.CharField(max_length=10, default='1.0', verbose_name="Phiên bản")
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_curricula',
        verbose_name="Người tạo",
        db_column='created_by'
    )
    approved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='approved_curricula',
        verbose_name="Người phê duyệt",
        db_column="approved_by"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(blank=True, null=True, verbose_name="Thời gian phê duyệt")

    class Meta:
        db_table = 'curricula'
        verbose_name = 'Chương trình đào tạo'
        verbose_name_plural = 'Các chương trình đào tạo'
        ordering = ['-academic_year', 'major']

    # @property
    # def subject_count(self):
    #     """Số lượng môn học trong chương trình"""
    #     return self.subjects.count()
    
    @property
    def is_active(self):
        """Kiểm tra chương trình có đang active không"""
        return self.status == 'active'
    
    def __str__(self):
        return f"{self.code} - {self.name} ({self.academic_year})"

    def save(self, *args, **kwargs):
        if self.status == 'approved' and not self.approved_at:
            self.approved_at = timezone.now()
        super().save(*args, **kwargs)
    
    def clean(self):
        """Validation logic"""
        if self.total_hours < (self.theory_hours + self.practice_hours):
            raise ValidationError("Tổng số giờ không được nhỏ hơn tổng giờ lý thuyết và thực hành")

class Course(models.Model):
    STATUS_CHOICES = [
        ('planned', 'Đã lập kế hoạch'),
        ('enrolling', 'Đang tuyển sinh'),
        ('ongoing', 'Đang đào tạo'),
        ('completed', 'Đã hoàn thành'),
        ('cancelled', 'Đã hủy'),
    ]
    
    curriculum = models.ForeignKey(
        Curriculum, 
        on_delete=models.CASCADE, 
        related_name='courses',
        verbose_name="Chương trình đào tạo",
        db_column="curriculum_id"
    )
    code = models.CharField(max_length=50, unique=True, verbose_name="Mã khóa học")
    name = models.CharField(max_length=255, verbose_name="Tên khóa học")
    start_year = models.IntegerField(verbose_name="Năm bắt đầu")
    end_year = models.IntegerField(verbose_name="Năm kết thúc")
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='planned',
        verbose_name="Trạng thái"
    )
    total_students = models.IntegerField(default=0, verbose_name="Tổng số sinh viên")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'courses'
        verbose_name = 'Khóa học'
        verbose_name_plural = 'Các khóa học'
        ordering = ['-start_year']

    def __str__(self):
        return f"{self.code} - {self.name} ({self.start_year}-{self.end_year})"

    @property
    def academic_year(self):
        return f"{self.start_year}-{self.end_year}"

class SubjectType(models.Model):
    code = models.CharField(max_length=20, unique=True, verbose_name="Mã loại môn học")
    name = models.CharField(max_length=100, verbose_name="Tên loại môn học")
    description = models.TextField(blank=True, null=True, verbose_name="Mô tả")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'subject_types'
        verbose_name = 'Loại môn học'
        verbose_name_plural = 'Các loại môn học'

    def __str__(self):
        return self.name


class Subject(models.Model):
    code = models.CharField(max_length=50, unique=True, verbose_name="Mã môn học")
    name = models.CharField(max_length=255, verbose_name="Tên môn học")
    curriculum = models.ForeignKey(
        Curriculum,
        on_delete=models.CASCADE,
        verbose_name="Chương trình đào tạo",
        blank=True
    )
    
    course = models.ForeignKey(
        Course, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="Khóa học"
    )

    subject_type = models.ForeignKey(
        SubjectType, 
        on_delete=models.SET_NULL, 
        null=True,
        verbose_name="Loại môn học",
        db_column="subject_type_id"
    )
    
    # Thông tin chung
    credits = models.DecimalField(
        max_digits=4, 
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Số tín chỉ",
        default=0
    )
    total_hours = models.IntegerField(default=0, verbose_name="Tổng số giờ")
    theory_hours = models.IntegerField(default=0, verbose_name="Số giờ lý thuyết")
    practice_hours = models.IntegerField(default=0, verbose_name="Số giờ thực hành")
    tests_hours = models.IntegerField(default=0, verbose_name="Số giờ kiểm tra")
    exam_hours = models.IntegerField(default=0, verbose_name="Số giờ thi")
    semester = models.IntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(8)],
        verbose_name="Học kỳ mặc định"
    )
    
    # Thông tin quản lý
    department = models.ForeignKey(
        Department, 
        on_delete=models.SET_NULL, 
        null=True,
        blank=True,
        verbose_name="Đơn vị quản lý",
        db_column="department_id"
    )
    subject_group = models.ForeignKey(
        SubjectGroup, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="Tổ bộ môn",
        db_column="subject_group_id"
    )
    
    # Thông tin bổ sung
    is_elective = models.BooleanField(default=False, verbose_name="Là môn tự chọn")
    elective_group = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name="Nhóm môn tự chọn"
    )
    prerequisites = models.TextField(blank=True, null=True, verbose_name="Điều kiện tiên quyết")
    learning_outcomes = models.TextField(blank=True, null=True, verbose_name="Chuẩn đầu ra")
    description = models.TextField(blank=True, null=True, verbose_name="Mô tả")
    
     # Thông tin hệ thống
    order_number = models.IntegerField(default=0, verbose_name="Thứ tự trong chương trình")
    original_code = models.CharField(max_length=20, verbose_name="Mã gốc từ file import")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
        
    class Meta:
        db_table = 'subjects'
        verbose_name = 'Môn học trong chương trình'
        verbose_name_plural = 'Các môn học trong chương trình'
        ordering = ['curriculum', 'order_number']

    def __str__(self):
        return f"{self.code} - {self.name} ({self.curriculum.code})"
        
    def clean(self):
        """Tự động tạo mã duy nhất nếu chưa có"""
        if not self.code:
            self.code = self.generate_unique_code()
        
    def generate_unique_code(self):
        """Tạo mã môn học duy nhất dựa trên mã chương trình và mã gốc"""
        base_code = self.original_code or re.sub(r'[^A-Z0-9]', '', self.name.upper())[:10]
        curriculum_prefix = self.curriculum.code.replace(' ', '_').upper()[:10]
        
        # Tạo mã cơ sở
        proposed_code = f"{curriculum_prefix}_{base_code}"
        
        # Kiểm tra và tạo mã duy nhất
        counter = 1
        unique_code = proposed_code
        while Subject.objects.filter(code=unique_code).exists():
            unique_code = f"{proposed_code}_{counter}"
            counter += 1
            
        return unique_code

    def save(self, *args, **kwargs):
        # Tự động tạo mã duy nhất nếu chưa có
        if not self.code:
            self.code = self.generate_unique_code()
        super().save(*args, **kwargs)

class SemesterAllocation(models.Model):
    base_subject = models.ForeignKey(
        Subject, 
        on_delete=models.CASCADE, 
        related_name='semester_allocations',
        verbose_name="Môn học trong chương trình",
        db_column="subject_id"
    )
    semester = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        verbose_name="Học kỳ"
    )
    credits = models.DecimalField(
        max_digits=4, 
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Số tín chỉ"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'semester_allocations'
        verbose_name = 'Phân bố học kỳ'
        verbose_name_plural = 'Phân bố học kỳ'
        unique_together = ['base_subject', 'semester']
        ordering = ['semester']

    def __str__(self):
        return f"{self.base_subject.code} - HK{self.semester} ({self.credits} tín chỉ)"

class Position(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Tên chức vụ")
    description = models.TextField(blank=True, null=True, verbose_name="Mô tả")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'positions'
        verbose_name = 'Chức vụ'
        verbose_name_plural = 'Các chức vụ'
        ordering = ['name']

    def __str__(self):
        return self.name

class Instructor(models.Model):
    code = models.CharField(max_length=20, unique=True, verbose_name="Mã giảng viên")
    full_name = models.CharField(max_length=255, verbose_name="Họ và tên")
    email = models.EmailField(blank=True, null=True, verbose_name="Email")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Số điện thoại")
    department = models.ForeignKey(
        Department, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name="instructors", 
        verbose_name="Khoa",
        db_column="department_id"
    )
    department_of_teacher_management = models.ForeignKey(
        Department, 
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_instructors",
        verbose_name="Khoa quản lý giảng viên"
    )
    position = models.ForeignKey(
        Position,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="instructors",
        verbose_name="Chức vụ",
        db_column="position_id"
    )
    
    subject_group = models.ForeignKey(
        SubjectGroup, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name="instructors",
        verbose_name="Tổ bộ môn",
        db_column="subject_group_id"
    )
    is_active = models.BooleanField(default=True, verbose_name="Đang hoạt động")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'instructors'
        verbose_name = 'Giảng viên'
        verbose_name_plural = 'Các giảng viên'
        ordering = ['full_name']

    def __str__(self):
        return f"{self.code} - {self.full_name}"

class Class(models.Model):
    """Lớp học - mỗi lớp học có thể học nhiều môn học"""
    code = models.CharField(max_length=50, unique=False, verbose_name="Mã lớp")
    name = models.CharField(max_length=255, verbose_name="Tên lớp")
    curriculum = models.ForeignKey(
        Curriculum,
        on_delete=models.CASCADE,
        related_name='classes',
        verbose_name="Chương trình đào tạo"
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='classes',
        verbose_name="Khóa học"
    )
    start_date = models.DateField(blank=True, null=True, verbose_name="Ngày bắt đầu")
    end_date = models.DateField(blank=True, null=True, verbose_name="Ngày kết thúc")
    is_combined = models.BooleanField(default=False, verbose_name="Là lớp ghép")
    combined_class_code = models.CharField(max_length=50, blank=True, null=True, verbose_name="Mã lớp ghép (nếu có)")
    description = models.TextField(blank=True, null=True, verbose_name="Mô tả")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'classes'
        verbose_name = 'Lớp học'
        verbose_name_plural = 'Các lớp học'
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def clean(self):
        """Validation logic"""
        # Chuyển chuỗi rỗng thành None cho các trường có thể null
        if self.start_date == '':
            self.start_date = None
        if self.end_date == '':
            self.end_date = None
        if self.combined_class_code == '':
            self.combined_class_code = None
            
        # Kiểm tra ngày kết thúc phải sau ngày bắt đầu
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError("Ngày kết thúc phải sau ngày bắt đầu")
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

class CombinedClass(models.Model):
    """Lớp học ghép - quản lý các lớp học được ghép với nhau"""
    code = models.CharField(max_length=50, unique=False, verbose_name="Mã lớp ghép")
    name = models.CharField(max_length=255, verbose_name="Tên lớp ghép")
    classes = models.ManyToManyField(
        Class,
        related_name='combined_classes',
        verbose_name="Các lớp được ghép"
    )
    # curriculum = models.ForeignKey(
    #     Curriculum,
    #     on_delete=models.CASCADE,
    #     related_name='combined_classes',
    #     verbose_name="Chương trình đào tạo"
    # )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='combined_classes',
        verbose_name="Môn học",
        db_column="subject_id",
        null=True, blank=True
    )
    description = models.TextField(blank=True, null=True, verbose_name="Mô tả")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'combined_classes'
        verbose_name = 'Lớp học ghép'
        verbose_name_plural = 'Các lớp học ghép'

    def __str__(self):
        return f"{self.code} - {self.name}"

# Cập nhật model TeachingAssignment để thêm trường lớp học
class TeachingAssignment(models.Model):
    curriculum_subject = models.ForeignKey(
        Subject, 
        on_delete=models.CASCADE, 
        related_name='teaching_assignments',
        verbose_name="Môn học trong chương trình"
    )
    instructor = models.ForeignKey(
        Instructor, 
        on_delete=models.CASCADE,
        related_name='teaching_assignments',
        verbose_name="Giảng viên"
    )
    # Thêm trường class (lớp học thường)
    class_obj = models.ForeignKey(
        Class,
        on_delete=models.CASCADE,
        related_name='teaching_assignments',
        verbose_name="Lớp học",
        null=True,
        blank=True
    )
    # Thêm trường combined_class (lớp học ghép)
    combined_class = models.ForeignKey(
        CombinedClass,
        on_delete=models.CASCADE,
        related_name='teaching_assignments',
        verbose_name="Lớp học ghép",
        null=True,
        blank=True
    )
    academic_year = models.CharField(max_length=20, verbose_name="Năm học")
    semester = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        verbose_name="Học kỳ"
    )
    is_main_instructor = models.BooleanField(default=True, verbose_name="Là giảng viên chính")
    
    # Thêm các trường thống kê
    student_count = models.IntegerField(default=0, verbose_name="Số lượng sinh viên")
    teaching_hours = models.IntegerField(default=0, verbose_name="Số giờ giảng dạy")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'teaching_assignments'
        verbose_name = 'Phân công giảng dạy'
        verbose_name_plural = 'Phân công giảng dạy'
        unique_together = [
            ['curriculum_subject', 'instructor', 'academic_year', 'semester', 'class_obj'],
            ['curriculum_subject', 'instructor', 'academic_year', 'semester', 'combined_class']
        ]
        ordering = ['-academic_year', 'semester']

    def __str__(self):
        role = "Chính" if self.is_main_instructor else "Phụ"
        class_name = self.class_obj.code if self.class_obj else self.combined_class.code if self.combined_class else "Không xác định"
        return f"{self.instructor.full_name} - {self.curriculum_subject.code} - {class_name} ({self.academic_year}-HK{self.semester}) - {role}"

    def save(self, *args, **kwargs):
        # Đảm bảo chỉ có một trong hai trường class_obj hoặc combined_class được set
        if self.class_obj and self.combined_class:
            raise ValidationError("Chỉ có thể chọn lớp học thường HOẶC lớp học ghép")
        super().save(*args, **kwargs)

    @property
    def class_type(self):
        """Xác định loại lớp học"""
        if self.class_obj:
            return "regular"
        elif self.combined_class:
            return "combined"
        return "unknown"

    @property
    def class_name(self):
        """Trả về tên lớp học"""
        if self.class_obj:
            return self.class_obj.name
        elif self.combined_class:
            return self.combined_class.name
        return "Không xác định"

    @property
    def class_code(self):
        """Trả về mã lớp học"""
        if self.class_obj:
            return self.class_obj.code
        elif self.combined_class:
            return self.combined_class.code
        return "Không xác định"

class ImportHistory(models.Model):
    STATUS_CHOICES = [
        ('success', 'Thành công'),
        ('partial', 'Thành công một phần'),
        ('failed', 'Thất bại'),
    ]
    
    curriculum = models.ForeignKey(
        Curriculum, 
        on_delete=models.SET_NULL, 
        null=True,
        blank=True,
        verbose_name="Chương trình đào tạo",
        db_column="curriculum_id"
    )
    file_name = models.CharField(max_length=255, verbose_name="Tên file")
    file_size = models.IntegerField(null=True, blank=True, verbose_name="Kích thước file")
    imported_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        verbose_name="Người import",
        db_column="imported_by"
    )
    record_count = models.IntegerField(default=0, verbose_name="Số bản ghi")
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='success',
        verbose_name="Trạng thái"
    )
    errors = models.JSONField(blank=True, null=True, verbose_name="Lỗi")
    additional_info = models.TextField(blank=True, null=True, verbose_name="Thông tin bổ sung")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'import_history'
        verbose_name = 'Lịch sử import'
        verbose_name_plural = 'Lịch sử import'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.file_name} - {self.created_at.strftime('%d/%m/%Y %H:%M')}"
