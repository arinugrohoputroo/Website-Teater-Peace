from django.db import models
from django.conf import settings


class EventConfig(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField(blank=True)
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = 'Event Configuration'
        ordering = ['key']

    def __str__(self):
        return f'{self.key}: {self.value}'

    @classmethod
    def get(cls, key, default=''):
        try:
            return cls.objects.get(key=key).value
        except cls.DoesNotExist:
            return default


class AuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    action = models.CharField(max_length=100)
    module = models.CharField(max_length=50)
    object_id = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Audit Log'

    def __str__(self):
        return f'{self.timestamp:%H:%M} - {self.user} - {self.action}'


def log_action(user, action, module, object_id='', description='', metadata=None, request=None):
    ip = None
    if request:
        ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR'))
        if ip and ',' in ip:
            ip = ip.split(',')[0].strip()
    AuditLog.objects.create(
        user=user,
        action=action,
        module=module,
        object_id=str(object_id),
        description=description,
        metadata=metadata or {},
        ip_address=ip,
    )
