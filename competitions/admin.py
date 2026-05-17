from django.contrib import admin
from config.admin_site import management_site
from .models import (
    Competition,
    Task,
    Participation,
    Solution,
    SolutionGradeEvent,
    Announcement,
    Subject,
    TaskType,
    TaskOption,
    TaskMatchingPair,
)


class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'order')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('order', 'name')


class TaskTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'order', 'auto_partial_enabled', 'partial_weight_percent')
    list_editable = ('auto_partial_enabled', 'partial_weight_percent')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('order', 'name')


class CompetitionAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'status',
        'audience',
        'level',
        'min_age',
        'max_age',
        'max_participants',
        'start_time',
        'end_time',
        'created_by',
        'created_at',
    )
    list_filter = ('status',)
    search_fields = ('title', 'description')
    list_editable = ('status',)
    list_per_page = 20
    date_hierarchy = 'created_at'


class TaskInline(admin.TabularInline):
    model = Task
    extra = 0


class TaskOptionInline(admin.TabularInline):
    model = TaskOption
    extra = 0
    ordering = ('order', 'pk')


class TaskMatchingPairInline(admin.TabularInline):
    model = TaskMatchingPair
    extra = 0
    ordering = ('order', 'pk')


class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'competition', 'subject', 'task_type', 'order', 'max_score', 'created_at')
    list_filter = ('competition', 'subject', 'task_type')
    search_fields = ('title', 'description')
    list_per_page = 25
    date_hierarchy = 'created_at'
    inlines = [TaskOptionInline, TaskMatchingPairInline]


class ParticipationAdmin(admin.ModelAdmin):
    list_display = ('user', 'competition', 'registered_at')
    list_filter = ('competition',)
    search_fields = ('user__username', 'user__email')
    date_hierarchy = 'registered_at'
    list_per_page = 30


class SolutionAdmin(admin.ModelAdmin):
    list_display = ('user', 'task', 'status', 'score', 'submitted_at')
    list_filter = ('status', 'task__competition')
    search_fields = ('content', 'user__username')
    list_editable = ('status', 'score')
    date_hierarchy = 'submitted_at'
    list_per_page = 30


class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'competition', 'is_pinned', 'created_at')
    list_filter = ('competition', 'is_pinned')
    search_fields = ('title', 'body')
    list_editable = ('is_pinned',)
    date_hierarchy = 'created_at'
    list_per_page = 25


class SolutionGradeEventAdmin(admin.ModelAdmin):
    list_display = ('solution', 'graded_by', 'from_score', 'to_score', 'from_status', 'to_status', 'created_at')
    list_filter = ('to_status', 'from_status', 'solution__task__competition')
    search_fields = ('solution__user__username', 'graded_by__username', 'note')
    date_hierarchy = 'created_at'
    list_per_page = 40


class TaskOptionAdmin(admin.ModelAdmin):
    list_display = ('task', 'text_short', 'is_correct', 'order')
    list_filter = ('task__competition', 'is_correct')
    search_fields = ('text',)
    ordering = ('task', 'order', 'pk')

    def text_short(self, obj):
        return (obj.text or '')[:50] + ('…' if len(obj.text or '') > 50 else '')
    text_short.short_description = 'Текст варианта'


class TaskMatchingPairAdmin(admin.ModelAdmin):
    list_display = ('task', 'order', 'left_short', 'right_short')
    search_fields = ('left_text', 'right_text')
    ordering = ('task', 'order', 'pk')
    list_filter = ('task__competition',)

    def left_short(self, obj):
        return (obj.left_text or '')[:42] + ('…' if len(obj.left_text or '') > 42 else '')
    left_short.short_description = 'Слева'

    def right_short(self, obj):
        return (obj.right_text or '')[:42] + ('…' if len(obj.right_text or '') > 42 else '')
    right_short.short_description = 'Справа'


# Регистрация в стандартном админе и в панели управления
for model, admin_class in [
    (Subject, SubjectAdmin),
    (TaskType, TaskTypeAdmin),
    (Competition, CompetitionAdmin),
    (Task, TaskAdmin),
    (Participation, ParticipationAdmin),
    (Solution, SolutionAdmin),
    (SolutionGradeEvent, SolutionGradeEventAdmin),
    (Announcement, AnnouncementAdmin),
    (TaskOption, TaskOptionAdmin),
    (TaskMatchingPair, TaskMatchingPairAdmin),
]:
    admin.site.register(model, admin_class)
    management_site.register(model, admin_class)
