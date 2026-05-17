from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('register/', views.RegistrationView.as_view(), name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('theme/', views.theme_save_view, name='theme_save'),
    path('email/test/', views.send_test_email_view, name='email_test'),
    path('password/change/', views.CustomPasswordChangeView.as_view(), name='password_change'),
    path('password/change/done/', views.CustomPasswordChangeDoneView.as_view(), name='password_change_done'),
    path('password/reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('password/reset/done/', views.CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password/reset/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password/reset/complete/', views.CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/edit/', views.ProfileEditView.as_view(), name='profile_edit'),
    path('notifications/', views.NotificationListView.as_view(), name='notifications'),
    path(
        'notifications/read-all/',
        views.notifications_mark_all_read,
        name='notifications_read_all',
    ),
    path('notifications/go/<int:pk>/', views.notification_follow, name='notification_go'),
    path('profile/<str:username>/', views.ProfilePublicView.as_view(), name='profile_public'),
]
