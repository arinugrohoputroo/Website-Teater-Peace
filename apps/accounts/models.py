from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email harus diisi')
        email = self.normalize_email(email)
        if 'username' not in extra_fields or not extra_fields['username']:
            extra_fields['username'] = email.split('@')[0]
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'ADMIN')
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        CUSTOMER = 'CUSTOMER', 'Customer'
        STAFF = 'STAFF', 'Staff'
        ADMIN = 'ADMIN', 'Admin'

    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=150)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.CUSTOMER)
    phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'name']

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name or self.username

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_panitia(self):
        return self.role in (self.Role.ADMIN, self.Role.STAFF)

    @property
    def is_customer(self):
        return self.role == self.Role.CUSTOMER


class StaffPermission(models.Model):
    class Module(models.TextChoices):
        TICKETING = 'ticketing', 'Ticketing'
        SNACK = 'snack', 'Snack'
        PAYMENT = 'payment', 'Pembayaran'
        REPORT = 'report', 'Laporan'
        PARTICIPANT = 'participant', 'Peserta'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='staff_permissions')
    module = models.CharField(max_length=20, choices=Module.choices)

    class Meta:
        unique_together = ['user', 'module']
        verbose_name = 'Staff Permission'

    def __str__(self):
        return f'{self.user.name} - {self.get_module_display()}'
