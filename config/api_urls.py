"""
Маршруты API (REST): JWT-аутентификация, CRUD соревнований и т.д.
"""
from django.urls import path, include

urlpatterns = [
    path('auth/', include('accounts.api_urls')),
    path('', include('competitions.api_urls')),
]
