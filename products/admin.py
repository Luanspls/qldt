# admin.py
from django.contrib import admin
from .models import (
    Department, SubjectGroup, Major, Curriculum, SubjectType, 
    Subject, SemesterAllocation, Instructor, TeachingAssignment, 
    Course, ImportHistory, Class, CombinedClass, Position
)


class SemesterAllocationInline(admin.TabularInline):
    model = SemesterAllocation
    extra = 1
    fields = ['semester', 'credits']
    
@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'created_at']
    search_fields = ['code', 'name']
    list_filter = ['created_at']

@admin.register(SubjectGroup)
class SubjectGroupAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'department', 'created_at']
    search_fields = ['code', 'name']
    list_filter = ['department', 'created_at']

@admin.register(Major)
class MajorAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'duration_years', 'total_credits', 'created_at']
    search_fields = ['code', 'name']
    list_filter = ['duration_years', 'created_at']

@admin.register(SubjectType)
class SubjectTypeAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'created_at']
    search_fields = ['code', 'name']

@admin.register(Curriculum)
class CurriculumAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'major', 'academic_year', 'status', 'total_credits', 'created_at']
    search_fields = ['code', 'name', 'academic_year']
    list_filter = ['major', 'status', 'academic_year', 'created_at']
    readonly_fields = ['created_at', 'updated_at', 'approved_at']
    # inlines = [CurriculumSubjectInline]
    
    def subject_count(self, obj):
        return obj.subjects.count()
    subject_count.short_description = 'Số môn học'
    
@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = [
        'code', 'name', 'subject_type', 'credits', 'semester', 
        'total_hours', 'theory_hours', 'practice_hours', 'exam_hours',
        'subject_group', 'department', 'is_elective', 'description', 'created_at'
    ]
    search_fields = ['code', 'name']
    list_filter = ['subject_type', 'is_elective', 'department']
    readonly_fields = ['created_at', 'updated_at']
    
    def curriculum_count(self, obj):
        return obj.curriculum.count()
    curriculum_count.short_description = 'Số chương trình'

@admin.register(SemesterAllocation)
class SemesterAllocationAdmin(admin.ModelAdmin):
    list_display = ['base_subject', 'semester', 'credits', 'created_at']
    list_filter = ['semester', 'created_at']
    search_fields = [
        'base_subject__code', 
        'base_subject__name',
        'base_subject__curriculum__code'
    ]

@admin.register(Instructor)
class InstructorAdmin(admin.ModelAdmin):
    list_display = ['code', 'full_name', 'department', 'subject_group', 'is_active']
    search_fields = ['code', 'full_name']
    list_filter = ['department', 'subject_group', 'is_active']

@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'created_at']
    search_fields = ['name']

@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'curriculum', 'course', 'is_combined', 'start_date', 'end_date']
    search_fields = ['code', 'name']
    list_filter = ['curriculum', 'course', 'is_combined', 'start_date']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(CombinedClass)
class CombinedClassAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'subject', 'get_classes_count']
    search_fields = ['code', 'name']
    list_filter = ['subject']
    filter_horizontal = ['classes']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_classes_count(self, obj):
        return obj.classes.count()
    get_classes_count.short_description = 'Số lớp được ghép'

@admin.register(TeachingAssignment)
class TeachingAssignmentAdmin(admin.ModelAdmin):
    list_display = [
        'instructor', 'get_subject_code', 'get_subject_name', 
        'get_class_info', 'academic_year', 'semester', 
        'is_main_instructor', 'student_count'
    ]
    list_filter = ['academic_year', 'semester', 'is_main_instructor', 'class_obj', 'combined_class']
    search_fields = [
        'instructor__full_name', 
        'curriculum_subject__subject__code', 
        'curriculum_subject__subject__name',
        'class_obj__code',
        'combined_class__code'
    ]
    
    def get_subject_code(self, obj):
        return obj.curriculum_subject.code
    get_subject_code.short_description = 'Mã môn học'
    
    def get_subject_name(self, obj):
        return obj.curriculum_subject.name
    get_subject_name.short_description = 'Tên môn học'
    
    def get_class_info(self, obj):
        if obj.class_obj:
            return f"{obj.class_obj.code} (Thường)"
        elif obj.combined_class:
            return f"{obj.combined_class.code} (Ghép)"
        return "Không xác định"
    get_class_info.short_description = 'Lớp học'

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'curriculum', 'start_year', 'end_year', 'status', 'total_students']
    search_fields = ['code', 'name']
    list_filter = ['curriculum', 'status', 'start_year']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(ImportHistory)
class ImportHistoryAdmin(admin.ModelAdmin):
    list_display = ['file_name', 'curriculum', 'imported_by', 'status', 'record_count', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['file_name', 'curriculum__name']
    readonly_fields = ['created_at']
