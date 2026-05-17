from django.urls import path

from . import views

app_name = 'hackathons'

urlpatterns = [
    path('', views.HackathonLandingView.as_view(), name='list'),
    path('create/', views.HackathonCreateView.as_view(), name='create'),
    path('<int:pk>/', views.HackathonDetailView.as_view(), name='detail'),
    path('<int:pk>/teams/', views.HackathonTeamsHubView.as_view(), name='teams'),
    path('<int:pk>/status/', views.HackathonQuickStatusView.as_view(), name='quick_status'),
    path('<int:pk>/edit/', views.HackathonUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.HackathonDeleteView.as_view(), name='delete'),
    path('<int:pk>/register/', views.HackathonRegisterView.as_view(), name='register'),
    path('<int:pk>/unregister/', views.HackathonUnregisterView.as_view(), name='unregister'),
    path('<int:pk>/teams/create/', views.HackathonTeamCreateView.as_view(), name='team_create'),
    path('<int:pk>/teams/<int:team_id>/request/', views.HackathonTeamRequestJoinView.as_view(), name='team_request_join'),
    path('<int:pk>/teams/leave/', views.HackathonTeamLeaveView.as_view(), name='team_leave'),
    path('<int:pk>/teams/dissolve/', views.HackathonTeamDissolveView.as_view(), name='team_dissolve'),
    path('<int:pk>/teams/requests/<int:member_id>/approve/', views.HackathonTeamRequestApproveView.as_view(), name='team_request_approve'),
    path('<int:pk>/teams/requests/<int:member_id>/reject/', views.HackathonTeamRequestRejectView.as_view(), name='team_request_reject'),
    path('<int:pk>/teams/captain/<int:user_id>/transfer/', views.HackathonTeamTransferCaptainView.as_view(), name='team_transfer_captain'),
    path(
        '<int:hackathon_id>/participants/<int:registration_id>/assign-team/',
        views.HackathonAssignTeamView.as_view(),
        name='assign_team',
    ),
    path('<int:pk>/chat/send/', views.HackathonChatPostView.as_view(), name='chat_send'),
    path('<int:hackathon_id>/participants/', views.HackathonParticipantsView.as_view(), name='participants'),
]
