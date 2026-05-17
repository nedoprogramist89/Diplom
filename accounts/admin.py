from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from config.admin_site import management_site
from .models import User, InAppNotification


@admin.register(InAppNotification)
class InAppNotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'kind', 'read_at', 'created_at')
    list_filter = ('kind', 'read_at')
    search_fields = ('title', 'body', 'user__username')
    raw_id_fields = ('user',)
    date_hierarchy = 'created_at'


class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'role', 'organization', 'theme', 'is_staff', 'is_superuser', 'is_active', 'date_joined')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'organization')
    ordering = ('-date_joined',)
    list_editable = ('role', 'is_active')  # быстрая правка в списке
    list_per_page = 25
    date_hierarchy = 'date_joined'
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Дополнительно', {'fields': ('role', 'organization', 'theme')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Дополнительно', {'fields': ('email', 'role', 'organization', 'theme')}),
    )


admin.site.register(User, UserAdmin)
management_site.register(User, UserAdmin)
management_site.register(InAppNotification, InAppNotificationAdmin)
