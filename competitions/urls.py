from django.urls import path
from . import views

app_name = 'competitions'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('home/', views.home_view, name='home_legacy'),
    path('results/', views.PublicResultsHubView.as_view(), name='public_results'),
    path('archive/', views.EventsArchiveView.as_view(), name='archive'),
    path('competitions/', views.CompetitionListView.as_view(), name='list'),
    path('competitions/<int:pk>/', views.CompetitionDetailView.as_view(), name='detail'),
    path('competitions/<int:pk>/status/', views.CompetitionQuickStatusView.as_view(), name='quick_status'),
    path('competitions/create/', views.CompetitionCreateView.as_view(), name='create'),
    path('competitions/<int:pk>/edit/', views.CompetitionUpdateView.as_view(), name='update'),
    path('competitions/<int:pk>/delete/', views.CompetitionDeleteView.as_view(), name='delete'),
    # Задачи
    path('competitions/<int:competition_id>/tasks/', views.TaskListView.as_view(), name='task_list'),
    path('tasks/<int:pk>/', views.TaskDetailView.as_view(), name='task_detail'),
    path('competitions/<int:competition_id>/tasks/create/', views.TaskCreateView.as_view(), name='task_create'),
    path('tasks/<int:pk>/edit/', views.TaskUpdateView.as_view(), name='task_update'),
    path('tasks/<int:pk>/delete/', views.TaskDeleteView.as_view(), name='task_delete'),
    # Участие
    path('competitions/<int:competition_id>/register/', views.RegisterParticipationView.as_view(), name='register'),
    path('competitions/<int:competition_id>/unregister/', views.UnregisterParticipationView.as_view(), name='unregister'),
    path('competitions/<int:competition_id>/participants/', views.CompetitionParticipantsView.as_view(), name='participants'),
    path('competitions/<int:pk>/certificate/', views.CompetitionCertificateView.as_view(), name='certificate'),
    # Решения
    path('tasks/<int:task_id>/submit/', views.SolutionSubmitView.as_view(), name='solution_submit'),
    path('tasks/<int:task_id>/solutions/', views.MySolutionsListView.as_view(), name='my_solutions'),
    path('tasks/<int:task_id>/solutions/all/', views.AllSolutionsForTaskView.as_view(), name='solution_list_all'),
    path('solutions/<int:pk>/grade/', views.SolutionGradeView.as_view(), name='solution_grade'),
    # Рейтинг
    path('competitions/<int:competition_id>/results/', views.CompetitionResultsView.as_view(), name='results'),
    path('competitions/<int:competition_id>/results/export/', views.CompetitionResultsExportCSVView.as_view(), name='results_export'),
    path(
        'competitions/<int:competition_id>/export/participants/',
        views.CompetitionParticipantsExportCSVView.as_view(),
        name='participants_export',
    ),
    path(
        'competitions/<int:competition_id>/export/solutions/',
        views.CompetitionSolutionsExportCSVView.as_view(),
        name='solutions_export',
    ),
    # Объявления
    path('competitions/<int:competition_id>/announcements/create/', views.AnnouncementCreateView.as_view(), name='announcement_create'),
    path('announcements/<int:pk>/edit/', views.AnnouncementUpdateView.as_view(), name='announcement_update'),
    path('announcements/<int:pk>/delete/', views.AnnouncementDeleteView.as_view(), name='announcement_delete'),
]
