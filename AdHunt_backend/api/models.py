from django.db import models
from django.contrib.auth.models import AbstractUser

class Role(models.TextChoices):
    USER = 'user', 'User'
    MODERATOR = 'moderator', 'Moderator'

class CustomUser(AbstractUser):
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.USER,
    )

