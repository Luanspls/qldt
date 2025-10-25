from django.contrib import admin
from django.urls import path, include
from .views import health_check, home

urlpatterns = [
    # path('admin/', admin.site.urls),
    path('health', health_check, name='health-check'),
    path('api/', include('products.urls')),
]