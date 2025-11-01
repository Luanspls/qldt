from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_page, name='home'),
    path('users/', views.users_list, name='users-list'),
    path('health/', views.health_check, name='health-check'),
    path('debug-setup/', views.debug_setup, name='debug-setup'),
    path('train_program_manager/', views.TrainProgramManagerView.as_view(), name='train_program_manager'),
    path('import-excel/', views.ImportExcelView.as_view(), name='import_excel'),
    path('download-excel-template/', views.ImportExcelView.as_view(), name='download_excel_template'),
    path('thong-ke/', views.ThongKeView.as_view(), name='thong_ke'),
    path('mon-hoc/<int:id>/', views.TrainProgramManagerView.as_view(), name='update_mon_hoc'),
    
    # API endpoints
    path('api/departments/', views.api_departments, name='api_departments'),
    path('api/subject-groups/', views.api_subject_groups, name='api_subject_groups'),
    path('api/curricula/', views.api_curricula, name='api_curricula'),
    path('api/courses/', views.api_courses, name='api_courses'),
    path('api/subjects/', views.api_subjects, name='api_subjects'),
]