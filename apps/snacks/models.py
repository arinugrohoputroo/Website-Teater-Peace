import re
import secrets
import string
import unicodedata

from django.conf import settings
from django.db import models


def normalize_committee_name(name):
    if not name:
        return ''
    text = unicodedata.normalize('NFKD', name)
    text = ''.join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = text.replace("’", "'").replace("`", "'").replace("´", "'")
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def generate_qr_token():
    alphabet = string.ascii_uppercase + string.digits
    alphabet = alphabet.replace('O', '').replace('0', '').replace('I', '').replace('1', '')
    body = ''.join(secrets.choice(alphabet) for _ in range(8))
    return f'TP26-{body}'


class CommitteeMember(models.Model):
    name = models.CharField(max_length=255, unique=True)
    normalized_name = models.CharField(max_length=255, db_index=True)
    member_code = models.CharField(max_length=10, unique=True)
    qr_token = models.CharField(max_length=32, unique=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['member_code']
        verbose_name = 'Anggota Panitia'
        verbose_name_plural = 'Anggota Panitia'

    def __str__(self):
        return f'{self.member_code} — {self.name}'

    def save(self, *args, **kwargs):
        self.normalized_name = normalize_committee_name(self.name)
        if not self.member_code:
            self.member_code = self._next_member_code()
        if not self.qr_token:
            self.qr_token = self._unique_token()
        super().save(*args, **kwargs)

    @classmethod
    def _next_member_code(cls):
        existing = cls.objects.values_list('member_code', flat=True)
        max_num = 0
        for code in existing:
            if code and code.startswith('P') and code[1:].isdigit():
                max_num = max(max_num, int(code[1:]))
        return f'P{max_num + 1:03d}'

    @classmethod
    def _unique_token(cls):
        for _ in range(20):
            token = generate_qr_token()
            if not cls.objects.filter(qr_token=token).exists():
                return token
        raise RuntimeError('Gagal membuat qr_token unik.')

    def regenerate_qr_token(self):
        self.qr_token = self._unique_token()
        self.save(update_fields=['qr_token', 'updated_at'])
        return self.qr_token


class SnackSession(models.Model):
    name = models.CharField(max_length=255)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['date', 'start_time']

    def __str__(self):
        return f'{self.name} - {self.date}'


class SnackClaim(models.Model):
    class DetectionMethod(models.TextChoices):
        QR = 'QR', 'QR'
        MANUAL = 'MANUAL', 'Manual'

    committee_member = models.ForeignKey(
        CommitteeMember,
        on_delete=models.CASCADE,
        related_name='snack_claims',
        null=True,
        blank=True,
    )
    participant = models.ForeignKey(
        'participants.Participant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    session = models.ForeignKey(SnackSession, on_delete=models.CASCADE)
    claimed_at = models.DateTimeField(auto_now_add=True)
    operator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    detection_method = models.CharField(
        max_length=10,
        choices=DetectionMethod.choices,
        default=DetectionMethod.QR,
    )
    qr_token_used = models.CharField(max_length=32, blank=True)

    class Meta:
        ordering = ['-claimed_at']
        constraints = [
            models.UniqueConstraint(
                fields=['committee_member', 'session'],
                name='unique_committee_session_snack',
                condition=models.Q(committee_member__isnull=False),
            ),
            models.UniqueConstraint(
                fields=['participant', 'session'],
                name='unique_participant_session_snack',
                condition=models.Q(participant__isnull=False),
            ),
        ]

    def __str__(self):
        subject = self.committee_member or self.participant
        return f'{subject} - {self.session}'

    @property
    def display_name(self):
        if self.committee_member_id:
            return self.committee_member.name
        if self.participant_id:
            return self.participant.name
        return '-'
