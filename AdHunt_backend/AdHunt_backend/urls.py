"""
URL configuration for AdHunt_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from api.views import (
    RegisterView, CustomTokenObtainPairView,
    AdvertisementListView, AdvertisementCreateView, AdvertisementDetailView,
    UserAdvertisementsView, ModeratorAdvertisementsView, FavoriteAdvertisementView,
    UserProfileView, ChangePasswordView
)
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions
from django.conf import settings
from django.conf.urls.static import static

schema_view = get_schema_view(
    openapi.Info(
        title="AdHunt API",
        default_version='v1',
        description="API для проекта AdHunt",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@adhunt.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/register/', RegisterView.as_view(), name='register'),
    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/profile/', UserProfileView.as_view(), name='user-profile'),
    path('api/profile/change-password/', ChangePasswordView.as_view(), name='change-password'),
    
    # Advertisement URLs
    path('api/advertisements/', AdvertisementListView.as_view(), name='advertisement-list'),
    path('api/advertisements/create/', AdvertisementCreateView.as_view(), name='advertisement-create'),
    path('api/advertisements/<int:pk>/', AdvertisementDetailView.as_view(), name='advertisement-detail'),
    path('api/advertisements/my/', UserAdvertisementsView.as_view(), name='user-advertisements'),
    path('api/advertisements/moderate/', ModeratorAdvertisementsView.as_view(), name='moderator-advertisements'),
    path('api/advertisements/moderate/<int:pk>/', ModeratorAdvertisementsView.as_view(), name='moderator-advertisement-detail'),
    path('api/advertisements/favorites/', FavoriteAdvertisementView.as_view(), name='favorite-advertisements'),
    path('api/advertisements/favorites/<int:pk>/', FavoriteAdvertisementView.as_view(), name='favorite-advertisement-detail'),
    
    # Swagger URLs
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)