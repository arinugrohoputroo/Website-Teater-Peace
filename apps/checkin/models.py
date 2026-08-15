from django.conf import settings
from django.db import models


class CheckIn(models.Model):
    ticket = models.OneToOneField('ticketing.Ticket', on_delete=models.CASCADE)
    participant = models.ForeignKey('participants.Participant', on_delete=models.CASCADE)
    checked_in_at = models.DateTimeField(auto_now_add=True)
    operator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class Meta:
        ordering = ['-checked_in_at']

    def __str__(self):
        return f'{self.participant} - {self.checked_in_at}'
