# models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver

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

    @property
    def subject_count(self):
        """Số lượng môn học trong chương trình"""
        return self.subjects.count()
    
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
    curriculum = models.ForeignKey(
        Curriculum, 
        on_delete=models.CASCADE, 
        related_name='subjects',
        verbose_name="Chương trình đào tạo",
        db_column="curriculum_id"
    )
    subject_type = models.ForeignKey(
        SubjectType, 
        on_delete=models.SET_NULL, 
        null=True,
        verbose_name="Loại môn học",
        db_column="subject_type_id"
    )
    code = models.CharField(max_length=20, verbose_name="Mã môn học")
    name = models.CharField(max_length=255, verbose_name="Tên môn học")
    credits = models.DecimalField(
        max_digits=4, 
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Số tín chỉ"
    )
    total_hours = models.IntegerField(default=0, verbose_name="Tổng số giờ")
    theory_hours = models.IntegerField(default=0, verbose_name="Số giờ lý thuyết")
    practice_hours = models.IntegerField(default=0, verbose_name="Số giờ thực hành")
    exam_hours = models.IntegerField(default=0, verbose_name="Số giờ kiểm tra/thi")
    semester = models.IntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        verbose_name="Học kỳ"
    )
    is_elective = models.BooleanField(default=False, verbose_name="Là môn tự chọn")
    elective_group = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name="Nhóm môn tự chọn"
    )
    min_elective_credits = models.DecimalField(
        max_digits=4, 
        decimal_places=2,
        default=0,
        verbose_name="Số tín chỉ tối thiểu phải chọn"
    )
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
    prerequisites = models.TextField(blank=True, null=True, verbose_name="Điều kiện tiên quyết")
    learning_outcomes = models.TextField(blank=True, null=True, verbose_name="Chuẩn đầu ra")
    description = models.TextField(blank=True, null=True, verbose_name="Mô tả")
    order_number = models.IntegerField(default=0, verbose_name="Thứ tự")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def remaining_hours(self):
        """Số giờ còn lại sau khi trừ các giờ đã phân bổ"""
        allocated = self.theory_hours + self.practice_hours + self.exam_hours
        return max(0, self.total_hours - allocated)
    
    def clean(self):
        """Validation for subject hours"""
        if self.total_hours < (self.theory_hours + self.practice_hours + self.exam_hours):
            raise ValidationError("Tổng số giờ không được nhỏ hơn tổng các loại giờ khác")

    class Meta:
        db_table = 'subjects'
        verbose_name = 'Môn học'
        verbose_name_plural = 'Các môn học'
        unique_together = ['curriculum', 'code']
        ordering = ['order_number', 'code']

    def __str__(self):
        return f"{self.code} - {self.name}"

    def save(self, *args, **kwargs):
        # Tự động tính tổng số giờ nếu chưa được set
        if not self.total_hours and (self.theory_hours or self.practice_hours or self.exam_hours):
            self.total_hours = (self.theory_hours or 0) + (self.practice_hours or 0) + (self.exam_hours or 0)
        super().save(*args, **kwargs)

@receiver(post_save, sender=Subject)
def update_curriculum_credits(sender, instance, **kwargs):
    """Cập nhật tổng số tín chỉ của chương trình khi môn học thay đổi"""
    curriculum = instance.curriculum
    total_credits = curriculum.subjects.aggregate(
        total=models.Sum('credits')
    )['total'] or 0
    curriculum.total_credits = total_credits
    curriculum.save()

class SemesterAllocation(models.Model):
    subject = models.ForeignKey(
        Subject, 
        on_delete=models.CASCADE, 
        related_name='semester_allocations',
        verbose_name="Môn học",
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
        unique_together = ['subject', 'semester']
        ordering = ['semester']

    def __str__(self):
        return f"{self.subject.code} - HK{self.semester} ({self.credits} tín chỉ)"


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
        verbose_name="Khoa",
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


class TeachingAssignment(models.Model):
    subject = models.ForeignKey(
        Subject, 
        on_delete=models.CASCADE, 
        related_name='teaching_assignments',
        verbose_name="Môn học",
        db_column="subject_id"
    )
    instructor = models.ForeignKey(
        Instructor, 
        on_delete=models.CASCADE,
        related_name='teaching_assignments',
        verbose_name="Giảng viên",
        db_column="instructor_id"
    )
    academic_year = models.CharField(max_length=20, verbose_name="Năm học")
    semester = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        verbose_name="Học kỳ"
    )
    is_main_instructor = models.BooleanField(default=True, verbose_name="Là giảng viên chính")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'teaching_assignments'
        verbose_name = 'Phân công giảng dạy'
        verbose_name_plural = 'Phân công giảng dạy'
        unique_together = ['subject', 'instructor', 'academic_year', 'semester']
        ordering = ['-academic_year', 'semester']

    def __str__(self):
        role = "Chính" if self.is_main_instructor else "Phụ"
        return f"{self.instructor.full_name} - {self.subject.code} ({self.academic_year}-HK{self.semester}) - {role}"


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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'import_history'
        verbose_name = 'Lịch sử import'
        verbose_name_plural = 'Lịch sử import'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.file_name} - {self.created_at.strftime('%d/%m/%Y %H:%M')}"
