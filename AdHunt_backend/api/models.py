from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

class Role(models.TextChoices):
    USER = 'user', 'User'
    MODERATOR = 'moderator', 'Moderator'

class CustomUser(AbstractUser):
    username = None  # Убираем поле username
    email = models.EmailField(_('email address'), unique=True)
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.USER,
    )
    last_name = models.CharField(max_length=150, verbose_name='Фамилия')
    first_name = models.CharField(max_length=150, verbose_name='Имя')
    middle_name = models.CharField(max_length=150, blank=True, null=True, verbose_name='Отчество')
    phone_number = models.CharField(max_length=15, unique=True, verbose_name='Номер телефона')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'phone_number']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.email

class AdvertisementStatus(models.TextChoices):
    PENDING = 'pending', 'На модерации'
    ACTIVE = 'active', 'Активное'
    REJECTED = 'rejected', 'Отклонено'

class Advertisement(models.Model):
    title = models.CharField(max_length=200, verbose_name='Название')
    description = models.TextField(verbose_name='Описание')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена')
    status = models.CharField(
        max_length=10,
        choices=AdvertisementStatus.choices,
        default=AdvertisementStatus.PENDING,
        verbose_name='Статус'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    author = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='advertisements',
        verbose_name='Автор'
    )

    class Meta:
        verbose_name = 'Объявление'
        verbose_name_plural = 'Объявления'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

class AdvertisementImage(models.Model):
    advertisement = models.ForeignKey(
        Advertisement,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name='Объявление'
    )
    image = models.ImageField(upload_to='advertisements/', verbose_name='Изображение')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')

    class Meta:
        verbose_name = 'Изображение объявления'
        verbose_name_plural = 'Изображения объявлений'

class FavoriteAdvertisement(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='Пользователь'
    )
    advertisement = models.ForeignKey(
        Advertisement,
        on_delete=models.CASCADE,
        related_name='favorited_by',
        verbose_name='Объявление'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')

    class Meta:
        verbose_name = 'Избранное объявление'
        verbose_name_plural = 'Избранные объявления'
        unique_together = ['user', 'advertisement']

    def __str__(self):
        return f"{self.user.email} - {self.advertisement.title}"

