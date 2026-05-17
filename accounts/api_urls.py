from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import api_views

urlpatterns = [
    path('token/', api_views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/', api_views.RegisterAPIView.as_view(), name='api_register'),
    path('me/', api_views.CurrentUserAPIView.as_view(), name='current_user'),
]
