from django.contrib import admin
from config.admin_site import management_site

from .models import (
    Hackathon,
    HackathonRegistration,
    HackathonChatMessage,
    HackathonTeam,
    HackathonTeamMember,
)


class HackathonRegistrationInline(admin.TabularInline):
    model = HackathonRegistration
    extra = 0
    readonly_fields = ('registered_at',)
    raw_id_fields = ('user',)


class HackathonAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'slug',
        'status',
        'format',
        'audience',
        'level',
        'min_age',
        'max_age',
        'max_teams',
        'starts_at',
        'ends_at',
        'created_by',
        'created_at',
    )
    list_filter = ('status', 'format')
    search_fields = ('title', 'tagline', 'description', 'results_summary', 'slug')
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'created_at'
    inlines = [HackathonRegistrationInline]


class HackathonRegistrationAdmin(admin.ModelAdmin):
    list_display = ('user', 'hackathon', 'team', 'team_name', 'looking_for_team', 'registered_at')
    list_filter = ('hackathon', 'looking_for_team')
    search_fields = ('user__username', 'team_name', 'comment')
    raw_id_fields = ('user',)
    date_hierarchy = 'registered_at'


class HackathonTeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'hackathon', 'created_by', 'created_at')
    list_filter = ('hackathon',)
    search_fields = ('name',)


class HackathonTeamMemberAdmin(admin.ModelAdmin):
    list_display = ('hackathon', 'team', 'user', 'role', 'joined_at')
    list_filter = ('hackathon', 'role')
    search_fields = ('user__username', 'team__name')


class HackathonChatMessageAdmin(admin.ModelAdmin):
    list_display = ('hackathon', 'team_name', 'channel', 'author', 'created_at')
    list_filter = ('hackathon', 'channel')
    search_fields = ('team_name', 'author__username', 'body')
    date_hierarchy = 'created_at'


for model, admin_cls in [
    (Hackathon, HackathonAdmin),
    (HackathonTeam, HackathonTeamAdmin),
    (HackathonTeamMember, HackathonTeamMemberAdmin),
    (HackathonRegistration, HackathonRegistrationAdmin),
    (HackathonChatMessage, HackathonChatMessageAdmin),
]:
    admin.site.register(model, admin_cls)
    management_site.register(model, admin_cls)
