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
    
    # def get_subjects_by_type(self, subject_type_name=None):
    #     """Lấy môn học theo loại"""
    #     subjects = self.subjects.all()
    #     if subject_type_name:
    #         subjects = subjects.filter(subject_type__name=subject_type_name)
    #     return subjects

    # def get_total_credits(self):
    #     """Tính tổng số tín chỉ"""
    #     return self.curriculum_subjects.aggregate(total=models.Sum('credits'))['total'] or 0

    # def get_total_hours(self):
    #     """Tính tổng số giờ"""
    #     return self.curriculum_subjects.aggregate(total=models.Sum('total_hours'))['total'] or 0

    # def update_totals(self):
    #     """Cập nhật tổng số tín chỉ và giờ từ các môn học"""
    #     from django.db.models import Sum
    #     aggregates = self.curriculum_subjects.aggregate(
    #         total_credits=Sum('credits'),
    #         total_hours=Sum('total_hours'),
    #         total_theory=Sum('theory_hours'),
    #         total_practice=Sum('practice_hours')
    #     )
        
    #     self.total_credits = aggregates['total_credits'] or 0
    #     self.total_hours = aggregates['total_hours'] or 0
    #     self.theory_hours = aggregates['total_theory'] or 0
    #     self.practice_hours = aggregates['total_practice'] or 0
    #     self.save()

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
    curricula = models.ManyToManyField(
        Curriculum,
        through='CurriculumSubject',
        related_name='subjects',
        verbose_name="Chương trình đào tạo",
        blank=True
    )

    subject_type = models.ForeignKey(
        SubjectType, 
        on_delete=models.SET_NULL, 
        null=True,
        verbose_name="Loại môn học",
        db_column="subject_type_id"
    )
    code = models.CharField(max_length=20, unique=True, verbose_name="Mã môn học")
    name = models.CharField(max_length=255, verbose_name="Tên môn học")
    
    credits = models.DecimalField(
        max_digits=4, 
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Số tín chỉ mặc định",
        default=0
    )
    total_hours = models.IntegerField(default=0, verbose_name="Tổng số giờ mặc định")
    theory_hours = models.IntegerField(default=0, verbose_name="Số giờ lý thuyết mặc định")
    practice_hours = models.IntegerField(default=0, verbose_name="Số giờ thực hành mặc định")
    exam_hours = models.IntegerField(default=0, verbose_name="Số giờ kiểm tra/thi mặc định")
    
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
        
    class Meta:
        db_table = 'subjects'
        verbose_name = 'Môn học'
        verbose_name_plural = 'Các môn học'
        # unique_together = []
        # constraints = [
        #     models.UniqueConstraint(fields=['code'], name='unique_subject_code')
        # ]
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.name}"
    
    @property
    def curriculum_count(self):
        """Số chương trình chứa môn học này"""
        return self.curricula.count()

class CurriculumSubject(models.Model):
    curriculum = models.ForeignKey(
        Curriculum, 
        on_delete=models.CASCADE,
        verbose_name="Chương trình đào tạo"
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        verbose_name="Môn học"
    )
    # Các trường đặc thù cho môn học trong chương trình cụ thể
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
    exam_hours = models.IntegerField(default=0, verbose_name="Số giờ kiểm tra/thi")
    order_number = models.IntegerField(default=0, verbose_name="Thứ tự")
    
    # Phân bố học kỳ có thể chuyển vào đây hoặc giữ trong SemesterAllocation
    semester = models.IntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        verbose_name="Học kỳ mặc định"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'curriculum_subjects'
        verbose_name = 'Môn học trong chương trình'
        verbose_name_plural = 'Các môn học trong chương trình'
        unique_together = ['curriculum', 'subject']
        ordering = ['order_number']

    def __str__(self):
        return f"{self.curriculum.code} - {self.subject.code}"
    
    def save(self, *args, **kwargs):
        # Nếu không có giá trị, sử dụng giá trị mặc định từ Subject
        if self.credits == 0:
            self.credits = self.subject.credits
        if self.total_hours == 0:
            self.total_hours = self.subject.total_hours
        if self.theory_hours == 0:
            self.theory_hours = self.subject.theory_hours
        if self.practice_hours == 0:
            self.practice_hours = self.subject.practice_hours
        if self.exam_hours == 0:
            self.exam_hours = self.subject.exam_hours
        super().save(*args, **kwargs)

@receiver(post_save, sender=CurriculumSubject)
def update_curriculum_credits(sender, instance, **kwargs):
    """Cập nhật tổng số tín chỉ của chương trình khi môn học thay đổi"""
    curriculum = instance.curriculum

class SemesterAllocation(models.Model):
    curriculum_subject = models.ForeignKey(
        CurriculumSubject, 
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
        unique_together = ['curriculum_subject', 'semester']
        ordering = ['semester']

    def __str__(self):
        return f"{self.curriculum_subject.subject.code} - HK{self.semester} ({self.credits} tín chỉ)"


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

class Class(models.Model):
    """Lớp học - mỗi lớp học có thể học nhiều môn học"""
    code = models.CharField(max_length=50, unique=True, verbose_name="Mã lớp")
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
    code = models.CharField(max_length=50, unique=True, verbose_name="Mã lớp ghép")
    name = models.CharField(max_length=255, verbose_name="Tên lớp ghép")
    classes = models.ManyToManyField(
        Class,
        related_name='combined_classes',
        verbose_name="Các lớp được ghép"
    )
    curriculum = models.ForeignKey(
        Curriculum,
        on_delete=models.CASCADE,
        related_name='combined_classes',
        verbose_name="Chương trình đào tạo"
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
        CurriculumSubject, 
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
        return f"{self.instructor.full_name} - {self.curriculum_subject.subject.code} - {class_name} ({self.academic_year}-HK{self.semester}) - {role}"

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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'import_history'
        verbose_name = 'Lịch sử import'
        verbose_name_plural = 'Lịch sử import'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.file_name} - {self.created_at.strftime('%d/%m/%Y %H:%M')}"
