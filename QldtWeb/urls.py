from django.contrib import admin
from django.urls import path, include
from products.views import health_check

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('products.urls')),
    path('', health_check, name='health-check'),
]