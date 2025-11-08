# admin.py
from django.contrib import admin
from .models import (
    Department, SubjectGroup, Major, Curriculum, SubjectType, 
    Subject, SemesterAllocation, Instructor, TeachingAssignment, 
    Course, ImportHistory, CurriculumSubject
)


class SemesterAllocationInline(admin.TabularInline):
    model = SemesterAllocation
    extra = 1
    fields = ['semester', 'credits']
    
class CurriculumSubjectInline(admin.TabularInline):
    model = CurriculumSubject
    extra = 1
    fields = ['subject', 'credits', 'total_hours', 'semester', 'order_number']

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
    inlines = [CurriculumSubjectInline]
    
    def subject_count(self, obj):
        return obj.subjects.count()
    subject_count.short_description = 'Số môn học'
    
@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = [
        'code', 'name', 'subject_type', 'credits', 
        'total_hours', 'is_elective', 'curriculum_count', 'created_at'
    ]
    search_fields = ['code', 'name']
    list_filter = ['subject_type', 'is_elective', 'department']
    readonly_fields = ['created_at', 'updated_at']
    
    def curriculum_count(self, obj):
        return obj.curricula.count()
    curriculum_count.short_description = 'Số chương trình'

@admin.register(CurriculumSubject)
class CurriculumSubjectAdmin(admin.ModelAdmin):
    list_display = [
        'curriculum', 'subject', 'credits', 'total_hours', 
        'semester', 'order_number', 'created_at'
    ]
    list_filter = ['curriculum', 'semester', 'created_at']
    search_fields = ['curriculum__code', 'curriculum__name', 'subject__code', 'subject__name']
    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['credits', 'total_hours', 'semester', 'order_number']
    inlines = [SemesterAllocationInline]

@admin.register(SemesterAllocation)
class SemesterAllocationAdmin(admin.ModelAdmin):
    list_display = ['curriculum_subject', 'semester', 'credits', 'created_at']
    list_filter = ['semester', 'created_at']
    search_fields = [
        'curriculum_subject__subject__code', 
        'curriculum_subject__subject__name',
        'curriculum_subject__curriculum__code'
    ]

@admin.register(Instructor)
class InstructorAdmin(admin.ModelAdmin):
    list_display = ['code', 'full_name', 'department', 'subject_group', 'is_active']
    search_fields = ['code', 'full_name']
    list_filter = ['department', 'subject_group', 'is_active']

@admin.register(TeachingAssignment)
class TeachingAssignmentAdmin(admin.ModelAdmin):
    list_display = ['instructor', 'get_subject_code', 'get_subject_name', 'academic_year', 'semester', 'is_main_instructor']
    list_filter = ['academic_year', 'semester', 'is_main_instructor']
    search_fields = ['instructor__full_name', 'curriculum_subject__subject__code', 'curriculum_subject__subject__name']
    
    def get_subject_code(self, obj):
        return obj.curriculum_subject.subject.code
    get_subject_code.short_description = 'Mã môn học'
    
    def get_subject_name(self, obj):
        return obj.curriculum_subject.subject.name
    get_subject_name.short_description = 'Tên môn học'

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
