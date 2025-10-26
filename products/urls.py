from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_page, name='home'),
    path('users/', views.users_list, name='users-list'),
    path('debug-setup/', views.debug_setup, name='debug-setup'),
]