"""
Главный маршрутизатор: веб-приложение соревнований по программированию.
В DEBUG статику из static/ отдаёт django.contrib.staticfiles (STATICFILES_DIRS).
Панель управления: /admin/ — отдельная панель с пользователями, соревнованиями и журналом аудита.
"""
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from config.admin_site import management_site

urlpatterns = [
    path('admin/', management_site.urls),
    path('accounts/', include('accounts.urls')),  # вход, регистрация, профиль — до корня
    path('api/', include('config.api_urls')),
    path('hackathons/', include('hackathons.urls')),
    path('', include('competitions.urls')),      # главная и соревнования
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
