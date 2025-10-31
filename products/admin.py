from django.contrib import admin
from .models import (
    Department, SubjectGroup, Major, Curriculum, SubjectType, 
    Subject, SemesterAllocation, Instructor, TeachingAssignment, 
    Course, ImportHistory
)

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

@admin.register(Curriculum)
class CurriculumAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'major', 'academic_year', 'status', 'total_credits', 'created_at']
    search_fields = ['code', 'name', 'academic_year']
    list_filter = ['major', 'status', 'academic_year', 'created_at']
    readonly_fields = ['created_at', 'updated_at', 'approved_at']

@admin.register(SubjectType)
class SubjectTypeAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'created_at']
    search_fields = ['code', 'name']

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = [
        'code', 'name', 'curriculum', 'subject_type', 'credits', 
        'total_hours', 'semester', 'is_elective'
    ]
    search_fields = ['code', 'name']
    list_filter = ['curriculum', 'subject_type', 'is_elective', 'semester', 'department']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(SemesterAllocation)
class SemesterAllocationAdmin(admin.ModelAdmin):
    list_display = ['subject', 'semester', 'credits', 'created_at']
    list_filter = ['semester', 'created_at']
    search_fields = ['subject__code', 'subject__name']

@admin.register(Instructor)
class InstructorAdmin(admin.ModelAdmin):
    list_display = ['code', 'full_name', 'department', 'subject_group', 'is_active']
    search_fields = ['code', 'full_name']
    list_filter = ['department', 'subject_group', 'is_active']

@admin.register(TeachingAssignment)
class TeachingAssignmentAdmin(admin.ModelAdmin):
    list_display = ['instructor', 'subject', 'academic_year', 'semester', 'is_main_instructor']
    list_filter = ['academic_year', 'semester', 'is_main_instructor']
    search_fields = ['instructor__full_name', 'subject__code', 'subject__name']

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
