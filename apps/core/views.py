from django.shortcuts import render, redirect

from apps.ticketing.models import ShowScript, TicketType
from apps.ticketing.services import ticket_types_with_stats


def home(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'role') and request.user.role in ('ADMIN', 'STAFF'):
            return redirect('dashboard:index')
    types = ticket_types_with_stats(active_only=True).prefetch_related('naskah_list')
    ticket_types = [t for t in types if t.remaining > 0]
    plays = ShowScript.objects.all()
    return render(request, 'public/home.html', {
        'ticket_types': ticket_types,
        'plays': plays,
    })
