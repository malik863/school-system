from django.contrib import admin



"""
# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin



# ==========================================
# BASE TENANT ADMIN
# ==========================================

class TenantAdmin(admin.ModelAdmin):

    exclude = ('school',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(school=request.user.school)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser and hasattr(obj, 'school_id'):
            if not obj.school_id:
                obj.school = request.user.school
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):

        if not request.user.is_superuser and hasattr(request.user, 'school') and request.user.school:
            if hasattr(db_field.remote_field.model, 'school'):
                kwargs["queryset"] = db_field.remote_field.model.objects.filter(school=request.user.school)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# ==========================================
# MODEL ADMIN REGISTRATIONS
# ==========================================

@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'created_at')
    search_fields = ('name', 'slug')

"""