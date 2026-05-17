from django.urls import path
from . import api_views

urlpatterns = [
    path('competitions/', api_views.CompetitionListCreateAPIView.as_view(), name='competition-list-create'),
    path('competitions/<int:pk>/', api_views.CompetitionRetrieveUpdateDestroyAPIView.as_view(), name='competition-detail'),
    path('competitions/<int:competition_id>/tasks/', api_views.TaskListCreateAPIView.as_view(), name='task-list-create'),
    path('tasks/<int:pk>/', api_views.TaskRetrieveUpdateDestroyAPIView.as_view(), name='task-detail'),
    path('competitions/<int:competition_id>/participations/', api_views.ParticipationListAPIView.as_view(), name='participation-list'),
    path('participations/mine/', api_views.MyParticipationsAPIView.as_view(), name='my-participations'),
    path('competitions/<int:competition_id>/register/', api_views.RegisterAPIView.as_view(), name='register'),
    path('competitions/<int:competition_id>/unregister/', api_views.UnregisterAPIView.as_view(), name='unregister'),
    path('tasks/<int:task_id>/solutions/', api_views.SolutionListAPIView.as_view(), name='solution-list'),
    path('tasks/<int:task_id>/submit/', api_views.SolutionSubmitAPIView.as_view(), name='solution-submit'),
    path('solutions/<int:pk>/', api_views.SolutionRetrieveUpdateAPIView.as_view(), name='solution-detail'),
    path('competitions/<int:competition_id>/results/', api_views.CompetitionResultsAPIView.as_view(), name='results'),
]
