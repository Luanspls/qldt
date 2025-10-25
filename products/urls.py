from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_page, name='home'),
    path('api/users/', views.users_list, name='users-list'),
    # path('users/<str:user_id>/', views.user_detail, name='user-detail'),
]