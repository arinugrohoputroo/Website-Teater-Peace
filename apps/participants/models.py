from django.db import models
from django.conf import settings


class Participant(models.Model):
    class Category(models.TextChoices):
        UMUM = 'UMUM', 'Umum'
        MAHASISWA = 'MAHASISWA', 'Mahasiswa'
        PELAJAR = 'PELAJAR', 'Pelajar'
        VIP = 'VIP', 'VIP'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='participant',
    )
    participant_code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    institution = models.CharField(max_length=200, blank=True)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.UMUM)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.participant_code})'

    def save(self, *args, **kwargs):
        if not self.participant_code:
            last = Participant.objects.order_by('-id').first()
            num = (last.id + 1) if last else 1
            self.participant_code = f'TP2026{num:05d}'
        super().save(*args, **kwargs)
