from django.contrib import admin
from django.urls import path, include
from products.views import health_check, home

urlpatterns = [
    # path('admin/', admin.site.urls),
    path('', health_check, name='health-check'),
    path('home/', home, name='home'),
    path('api/', include('products.urls')),
]