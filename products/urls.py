from django.urls import path
from . import views

urlpatterns = [
    path('users/', views.users_list, name='users-list'),
    path('users/<str:user_id>/', views.user_detail, name='user-detail'),
]