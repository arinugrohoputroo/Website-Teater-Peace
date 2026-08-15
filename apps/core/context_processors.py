from .models import EventConfig


def event_context(request):
    return {
        'event_name': EventConfig.get('event_name', 'TEATER PEACE'),
        'event_date': EventConfig.get('event_date', ''),
        'event_venue': EventConfig.get('event_venue', ''),
        'event_contact': EventConfig.get('event_contact', '085712089906 (Ari Nugroho)'),
    }
