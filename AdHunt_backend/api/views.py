from django.shortcuts import render, get_object_or_404

from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth.models import User
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.serializers import ModelSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import CustomUser, Advertisement, AdvertisementImage, FavoriteAdvertisement, AdvertisementStatus
from rest_framework import serializers
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.parsers import MultiPartParser, FormParser
from django.db.models import Q
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
import boto3
import os
import json

class RegisterSerializer(ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    
    class Meta:
        model = CustomUser
        fields = ['email', 'password', 'last_name', 'first_name', 'middle_name', 'phone_number']
        extra_kwargs = {
            'password': {'write_only': True},
            'last_name': {'required': True},
            'first_name': {'required': True},
            'email': {'required': True},
            'phone_number': {'required': True},
            'middle_name': {'required': False}
        }

    def validate_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("Пользователь с таким email уже существует")
        return value

    def validate_phone_number(self, value):
        if CustomUser.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("Пользователь с таким номером телефона уже существует")
        return value

    def create(self, validated_data):
        user = CustomUser.objects.create_user(**validated_data)
        user.role = 'user'  # Default role
        user.save()
        return user

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['email', 'last_name', 'first_name', 'middle_name', 'phone_number', 'role']
        read_only_fields = ['role']

class UserProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['email', 'last_name', 'first_name', 'middle_name', 'phone_number']

    def validate_email(self, value):
        if CustomUser.objects.filter(email=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("Пользователь с таким email уже существует")
        return value

    def validate_phone_number(self, value):
        if CustomUser.objects.filter(phone_number=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("Пользователь с таким номером телефона уже существует")
        return value

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={
            200: UserProfileSerializer,
        },
        operation_description="Получение профиля пользователя"
    )
    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data)

    @swagger_auto_schema(
        request_body=UserProfileUpdateSerializer,
        responses={
            200: UserProfileSerializer,
            400: "Ошибка валидации данных"
        },
        operation_description="Обновление профиля пользователя"
    )
    def put(self, request):
        serializer = UserProfileUpdateSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(UserProfileSerializer(request.user).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = CustomUser.EMAIL_FIELD

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Добавляем роль пользователя в токен
        token['role'] = user.role
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        return {'access': data['access']}  # Return only the access token

class RegisterView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        request_body=RegisterSerializer,
        responses={
            201: openapi.Response(
                description="Пользователь успешно зарегистрирован",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'access': openapi.Schema(type=openapi.TYPE_STRING, description='JWT токен доступа')
                    }
                )
            ),
            400: openapi.Response(
                description="Ошибка валидации данных",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'field_name': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING))
                    }
                )
            )
        },
        operation_description="Регистрация нового пользователя"
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token_serializer = CustomTokenObtainPairSerializer()
            token = token_serializer.get_token(user)
            return Response({'access': str(token.access_token)}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

    @swagger_auto_schema(
        request_body=CustomTokenObtainPairSerializer,
        responses={
            200: openapi.Response(
                description="Успешная авторизация",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'access': openapi.Schema(type=openapi.TYPE_STRING, description='JWT токен доступа')
                    }
                )
            ),
            401: openapi.Response(
                description="Неверные учетные данные",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'detail': openapi.Schema(type=openapi.TYPE_STRING, description='Сообщение об ошибке')
                    }
                )
            )
        },
        operation_description="Получение JWT токена для авторизации"
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

class AdvertisementImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdvertisementImage
        fields = ['id', 'image']

class AdvertisementSerializer(serializers.ModelSerializer):
    images = AdvertisementImageSerializer(many=True, read_only=True)
    author = UserProfileSerializer(read_only=True)
    is_favorite = serializers.BooleanField(read_only=True)

    class Meta:
        model = Advertisement
        fields = ['id', 'title', 'description', 'price', 'status', 'created_at', 'updated_at', 'author', 'images', 'is_favorite']

    def get_is_favorite(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return FavoriteAdvertisement.objects.filter(user=request.user, advertisement=obj).exists()
        return False

class AdvertisementUpdateSerializer(serializers.ModelSerializer):
    images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Advertisement
        fields = ['title', 'description', 'price', 'images']

    def update(self, instance, validated_data):
        images = validated_data.pop('images', [])
        instance.title = validated_data.get('title', instance.title)
        instance.description = validated_data.get('description', instance.description)
        instance.price = validated_data.get('price', instance.price)
        instance.status = AdvertisementStatus.PENDING
        instance.save()

        if images:
            # Удаляем старые изображения
            instance.images.all().delete()
            # Создаем новые изображения
            for image in images:
                AdvertisementImage.objects.create(
                    advertisement=instance,
                    image=image
                )

        return instance

class AdvertisementCreateSerializer(serializers.ModelSerializer):
    images = serializers.ListField(
        child=serializers.ImageField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Advertisement
        fields = ['title', 'description', 'price', 'images']

    def create(self, validated_data):
        images = validated_data.pop('images', [])
        advertisement = Advertisement.objects.create(
            **validated_data,
            author=self.context['request'].user,
            status=AdvertisementStatus.PENDING
        )
        
        for image in images:
            AdvertisementImage.objects.create(
                advertisement=advertisement,
                image=image
            )

        notify_queue(advertisement)
        
        return advertisement

def notify_queue(advertisement):
    if os.getenv("USE_YMQ") != "True":
        return

    client = boto3.client(
        'sqs',
        region_name='ru-central1',
        endpoint_url='https://message-queue.api.cloud.yandex.net',
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
    )

    queue_url = os.getenv("YMQ_ADS_QUEUE_URL")
    message = {
        "id": advertisement.id,
        "title": advertisement.title,
        "author": advertisement.author.email,
        "status": advertisement.status
    }

    client.send_message(
        QueueUrl=queue_url,
        MessageBody=json.dumps(message)
    )


class IsModerator(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.role == 'moderator'

class AdvertisementListView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        responses={
            200: AdvertisementSerializer(many=True),
        },
        operation_description="Получение списка всех объявлений"
    )
    def get(self, request):
        advertisements = Advertisement.objects.filter(status=AdvertisementStatus.ACTIVE)
        serializer = AdvertisementSerializer(advertisements, many=True, context={'request': request})
        return Response(serializer.data)

class AdvertisementCreateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'title',
                openapi.IN_FORM,
                description='Название объявления',
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'description',
                openapi.IN_FORM,
                description='Описание объявления',
                type=openapi.TYPE_STRING,
                required=True
            ),
            openapi.Parameter(
                'price',
                openapi.IN_FORM,
                description='Цена',
                type=openapi.TYPE_NUMBER,
                required=True
            ),
            openapi.Parameter(
                'images',
                openapi.IN_FORM,
                description='Изображения объявления',
                type=openapi.TYPE_FILE,
                required=False
            ),
        ],
        responses={
            201: AdvertisementSerializer,
            400: "Ошибка валидации данных"
        },
        operation_description="Создание нового объявления"
    )
    def post(self, request):
        serializer = AdvertisementCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            advertisement = serializer.save()
            return Response(AdvertisementSerializer(advertisement, context={'request': request}).data, 
                          status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AdvertisementDetailView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        responses={
            200: AdvertisementSerializer,
            404: "Объявление не найдено"
        },
        operation_description="Получение детальной информации об объявлении"
    )
    def get(self, request, pk):
        advertisement = get_object_or_404(Advertisement, pk=pk)
        serializer = AdvertisementSerializer(advertisement, context={'request': request})
        return Response(serializer.data)

    @swagger_auto_schema(
        request_body=AdvertisementUpdateSerializer,
        responses={
            200: AdvertisementSerializer,
            400: "Ошибка валидации данных",
            403: "Нет прав на редактирование",
            404: "Объявление не найдено"
        },
        operation_description="Редактирование объявления"
    )
    def put(self, request, pk):
        advertisement = get_object_or_404(Advertisement, pk=pk)
        if advertisement.author != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN)
        
        serializer = AdvertisementUpdateSerializer(advertisement, data=request.data, partial=True)
        if serializer.is_valid():
            updated_advertisement = serializer.save()
            return Response(AdvertisementSerializer(updated_advertisement, context={'request': request}).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        responses={
            204: "Объявление успешно удалено",
            404: "Объявление не найдено",
            403: "Нет прав на удаление"
        },
        operation_description="Удаление объявления"
    )
    def delete(self, request, pk):
        advertisement = get_object_or_404(Advertisement, pk=pk)
        if advertisement.author != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN)
        advertisement.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class UserAdvertisementsView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={
            200: AdvertisementSerializer(many=True),
        },
        operation_description="Получение списка объявлений пользователя"
    )
    def get(self, request):
        advertisements = Advertisement.objects.filter(author=request.user)
        serializer = AdvertisementSerializer(advertisements, many=True, context={'request': request})
        return Response(serializer.data)

class ModeratorAdvertisementsView(APIView):
    permission_classes = [IsAuthenticated, IsModerator]

    @swagger_auto_schema(
        responses={
            200: AdvertisementSerializer(many=True),
        },
        operation_description="Получение списка объявлений на модерацию"
    )
    def get(self, request):
        advertisements = Advertisement.objects.filter(status=AdvertisementStatus.PENDING)
        serializer = AdvertisementSerializer(advertisements, many=True, context={'request': request})
        return Response(serializer.data)

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'status': openapi.Schema(type=openapi.TYPE_STRING, enum=['active', 'rejected'])
            }
        ),
        responses={
            200: AdvertisementSerializer,
            400: "Ошибка валидации данных",
            403: "Нет прав на модерацию"
        },
        operation_description="Изменение статуса объявления"
    )
    def post(self, request, pk):
        advertisement = get_object_or_404(Advertisement, pk=pk)
        new_status = request.data.get('status')
        
        if new_status not in ['active', 'rejected']:
            return Response({'error': 'Неверный статус'}, status=status.HTTP_400_BAD_REQUEST)
        
        advertisement.status = new_status
        advertisement.save()
        
        serializer = AdvertisementSerializer(advertisement, context={'request': request})
        return Response(serializer.data)

class FavoriteAdvertisementView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={
            200: AdvertisementSerializer(many=True),
        },
        operation_description="Получение списка избранных объявлений"
    )
    def get(self, request):
        favorites = FavoriteAdvertisement.objects.filter(user=request.user)
        advertisements = [fav.advertisement for fav in favorites]
        serializer = AdvertisementSerializer(advertisements, many=True, context={'request': request})
        return Response(serializer.data)

    @swagger_auto_schema(
        responses={
            201: "Объявление добавлено в избранное",
            400: "Объявление уже в избранном",
            404: "Объявление не найдено"
        },
        operation_description="Добавление объявления в избранное"
    )
    def post(self, request, pk):
        advertisement = get_object_or_404(Advertisement, pk=pk)
        
        if FavoriteAdvertisement.objects.filter(user=request.user, advertisement=advertisement).exists():
            return Response({'error': 'Объявление уже в избранном'}, status=status.HTTP_400_BAD_REQUEST)
        
        FavoriteAdvertisement.objects.create(user=request.user, advertisement=advertisement)
        return Response(status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        responses={
            204: "Объявление удалено из избранного",
            404: "Объявление не найдено в избранном"
        },
        operation_description="Удаление объявления из избранного"
    )
    def delete(self, request, pk):
        favorite = get_object_or_404(FavoriteAdvertisement, user=request.user, advertisement_id=pk)
        favorite.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)
    confirm_password = serializers.CharField(required=True, write_only=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Неверный текущий пароль")
        return value

    def validate_new_password(self, value):
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Пароли не совпадают"})
        return data

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        request_body=ChangePasswordSerializer,
        responses={
            200: openapi.Response(
                description="Пароль успешно изменен",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description='Сообщение об успешной смене пароля')
                    }
                )
            ),
            400: "Ошибка валидации данных"
        },
        operation_description="Смена пароля пользователя"
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Пароль успешно изменен'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
