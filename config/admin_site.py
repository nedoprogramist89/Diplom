"""
Отдельная панель управления: пользователи, соревнования, журнал аудита.
Подключается по пути /admin/ (заменяет стандартный админ).
"""
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.admin.models import LogEntry
from django.urls import reverse
from django.utils.html import format_html


# Прокси-модель для отображения в меню как «Журнал аудита»
class AuditLog(LogEntry):
    class Meta:
        proxy = True
        app_label = 'admin'  # LogEntry из django.contrib.admin
        verbose_name = 'Запись журнала'
        verbose_name_plural = 'Журнал аудита'


class ManagementAdminSite(AdminSite):
    site_header = 'Панель управления CompetitionHub'
    site_title = 'Панель управления'
    index_title = 'Администрирование сайта'


# Единственная панель — используем её вместо стандартного admin.site
management_site = ManagementAdminSite(name='management')


class LogEntryAdmin(admin.ModelAdmin):
    """Журнал аудита: все действия в панели управления (только просмотр)."""
    list_display = ('action_time', 'user_link', 'content_type', 'object_repr_short', 'action_flag_badge', 'change_message_short')
    list_filter = ('action_flag', 'content_type')
    search_fields = ('user__username', 'object_repr', 'change_message')
    ordering = ('-action_time',)
    date_hierarchy = 'action_time'
    readonly_fields = ('action_time', 'user', 'content_type', 'object_id', 'object_repr', 'action_flag', 'change_message')
    list_per_page = 50

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def user_link(self, obj):
        if not obj.user:
            return '—'
        return format_html('<a href="?user__id__exact={}">{}</a>', obj.user_id, obj.user.get_username())
    user_link.short_description = 'Пользователь'

    def object_repr_short(self, obj):
        r = (obj.object_repr or '')[:60]
        text = r + '…' if len(obj.object_repr or '') > 60 else (r or '—')
        try:
            from django.contrib.contenttypes.models import ContentType
            ct = ContentType.objects.get_for_id(obj.content_type_id)
            url = reverse(
                'management:%s_%s_change' % (ct.app_label, ct.model),
                args=(obj.object_id,),
            )
            return format_html('<a href="{}">{}</a>', url, text)
        except Exception:
            return text
    object_repr_short.short_description = 'Объект'

    def action_flag_badge(self, obj):
        flags = {1: ('Добавление', '#28a745'), 2: ('Изменение', '#ffc107'), 3: ('Удаление', '#dc3545')}
        text, color = flags.get(obj.action_flag, ('—', '#6c757d'))
        return format_html('<span style="color:{};">{}</span>', color, text)
    action_flag_badge.short_description = 'Действие'

    def change_message_short(self, obj):
        msg = (obj.change_message or '')[:80]
        return msg + '…' if len(obj.change_message or '') > 80 else (msg or '—')
    change_message_short.short_description = 'Изменения'


# Журнал аудита (только просмотр)
management_site.register(AuditLog, LogEntryAdmin)

# Группы — удобный список и поиск
from django.contrib.auth.models import Group
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    filter_horizontal = ('permissions',)
management_site.register(Group, GroupAdmin)
