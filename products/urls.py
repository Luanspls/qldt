from django.urls import path
from . import views
from QldtWeb.views import health_check


urlpatterns = [
    path('', views.home_page, name='home'),
    path('users/', views.users_list, name='users-list'),
    path('health/', health_check, name='health-check'),
    path('train_program/', views.TrainProgramManagerView.as_view(), name='train_program'),
    path('train-program/<int:id>/', views.TrainProgramManagerView.as_view(), name='train_program_update'),
    path('download-excel-template/', views.ImportExcelView.as_view(), name='download_excel_template'),
    path('import-excel/', views.ImportExcelView.as_view(), name='import_excel'),
    path('thong-ke/', views.ThongKeView.as_view(), name='thong_ke'),
    path('mon-hoc/<int:id>/', views.TrainProgramManagerView.as_view(), name='update_mon_hoc'),
    path('teaching-management/', views.TeachingManagementView.as_view(), name='teaching_management'),
    
    # API endpoints
    path('api/departments/', views.api_departments, name='api_departments'),
    path('api/subject-groups/', views.api_subject_groups, name='api_subject_groups'),
    path('api/curricula/', views.api_curricula, name='api_curricula'),
    path('api/courses/', views.api_courses, name='api_courses'),
    path('api/subjects/', views.api_subjects, name='api_subjects'),
    path('api/all-subjects/', views.api_all_subjects, name='api_all_subjects'),
    path('api/subjects/create/', views.api_create_subject, name='api_create_subject'),
    path('api/subject-types/', views.api_subject_types, name='api_subject_types'),
    path('api/majors/', views.api_majors, name='api_majors'),
    path('api/curriculum/create/', views.create_curriculum, name='create_curriculum'),
    path('import-teaching-data/<str:object_type>/', views.ImportTeachingDataView.as_view(), name='import_teaching_data'),
    path('api/search-instructors/', views.api_search_instructors, name='api_search_instructors'),
    
    # URL mới cho quản lý lớp học và phân công giảng dạy
    path('api/classes/', views.api_classes, name='api_classes'),
    path('api/classes/create/', views.api_create_class, name='api_create_class'),
    path('api/combined-classes/', views.api_combined_classes, name='api_combined_classes'),
    path('api/combined-classes/create/', views.api_create_combined_class, name='api_create_combined_class'),
    path('api/teaching-assignments/', views.api_teaching_assignments, name='api_teaching_assignments'),
    path('api/teaching-assignments/create/', views.api_create_teaching_assignment, name='api_create_teaching_assignment'),
    path('api/teaching-statistics/', views.api_teaching_statistics, name='api_teaching_statistics'),
    path('api/instructors/', views.api_instructors, name='api_instructors'),
    path('api/instructors/create/', views.api_create_instructor, name='api_create_instructor'),
    # path('api/curriculum-subjects/', views.api_curriculum_subjects, name='api_curriculum_subjects'),
    path('api/get-sheet-names/', views.api_get_sheet_names, name='api_get_sheet_names'),

    # API cho Lớp học
    path('api/classes/<int:id>/', views.api_class_detail, name='api_class_detail'),
    path('api/classes/update/<int:id>/', views.api_update_class, name='api_update_class'),
    path('api/classes/delete/<int:id>/', views.api_delete_class, name='api_delete_class'),
    
    # API cho Lớp học ghép
    path('api/combined-classes/<int:id>/', views.api_combined_class_detail, name='api_combined_class_detail'),
    path('api/combined-classes/update/<int:id>/', views.api_update_combined_class, name='api_update_combined_class'),
    path('api/combined-classes/delete/<int:id>/', views.api_delete_combined_class, name='api_delete_combined_class'),
    
    # API cho Giảng viên
    path('api/instructors/<int:id>/', views.api_instructor_detail, name='api_instructor_detail'),
    path('api/instructors/update/<int:id>/', views.api_update_instructor, name='api_update_instructor'),
    path('api/instructors/delete/<int:id>/', views.api_delete_instructor, name='api_delete_instructor'),
    
    # API cho Phân công giảng dạy
    path('api/teaching-assignments/<int:id>/', views.api_teaching_assignment_detail, name='api_teaching_assignment_detail'),
    path('api/teaching-assignments/update/<int:id>/', views.api_update_teaching_assignment, name='api_update_teaching_assignment'),
    path('api/teaching-assignments/delete/<int:id>/', views.api_delete_teaching_assignment, name='api_delete_teaching_assignment'),
]
