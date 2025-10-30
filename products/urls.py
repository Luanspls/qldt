from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_page, name='home'),
    path('users/', views.users_list, name='users-list'),
    path('health/', views.health_check, name='health-check'),
    path('debug-setup/', views.debug_setup, name='debug-setup'),
    path('train_program', views.train_program, name='train_program'),
]
