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
    path('download-excel-template/', views.ImportExcelView.as_view(), name='download_excel_template'),
    path('thong-ke/', views.ThongKeView.as_view(), name='thong_ke'),
    path('mon-hoc/<int:id>/', views.TrainProgramManagerView.as_view(), name='update_mon_hoc'),
    
    # API endpoints
    path('api/departments/', views.api_departments, name='api_departments'),
    path('api/subject-groups/', views.api_subject_groups, name='api_subject_groups'),
    path('api/curricula/', views.api_curricula, name='api_curricula'),
    path('api/courses/', views.api_courses, name='api_courses'),
    path('api/subjects/', views.api_subjects, name='api_subjects'),
    path('api/subjects/create/', views.api_create_subject, name='api_create_subject'),
    path('api/subject-types/', views.api_subject_types, name='api_subject_types'),
    path('api/majors/', views.api_majors, name='api_majors'),
    path('api/curriculum/create/', views.create_curriculum, name='create_curriculum'),
]
