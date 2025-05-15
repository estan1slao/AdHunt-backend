from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('role',)}),  # Добавляем поле role
    )
    list_display = UserAdmin.list_display + ('role',)  # Отображаем роль в списке пользователей

admin.site.register(CustomUser, CustomUserAdmin)