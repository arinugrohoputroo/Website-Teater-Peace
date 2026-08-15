from django.contrib import admin
from .models import Participant


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ['participant_code', 'name', 'phone', 'email', 'institution', 'category']
    search_fields = ['name', 'phone', 'email', 'participant_code']
    list_filter = ['category']
