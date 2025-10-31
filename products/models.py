# models.py
from django.db import models
from django.contrib.auth.models import User

class Department(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class SubjectGroup(models.Model):
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True)
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Major(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    duration_years = models.IntegerField(default=3)
    total_credits = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Curriculum(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Bản nháp'),
        ('approved', 'Đã phê duyệt'),
        ('active', 'Đang áp dụng'),
        ('archived', 'Lưu trữ'),
    ]
    
    major = models.ForeignKey(Major, on_delete=models.CASCADE)
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    academic_year = models.CharField(max_length=20)
    description = models.TextField(blank=True, null=True)
    total_credits = models.IntegerField(default=0)
    total_hours = models.IntegerField(default=0)
    theory_hours = models.IntegerField(default=0)
    practice_hours = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    version = models.CharField(max_length=10, default='1.0')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_curricula')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='approved_curricula')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_at = models.DateTimeField(blank=True, null=True)

# ... tiếp tục với các models khác tương ứng
