from django.contrib import admin

# Register your models here.
from django.contrib.auth.admin import UserAdmin
from accounts.models import User


from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'get_full_name', 'role', 'school', 'is_staff')
    list_filter = ('role', 'school', 'is_staff', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('معلومات المدرسة والدور', {'fields': ('school', 'role', 'phone_number')}),
    )