from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from .views import health_check

def home(request):
    return HttpResponse("QLDT App is working!")

urlpatterns = [
    path('', home, name='home'),
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health-check'),
    path('', include('products.urls')),
]