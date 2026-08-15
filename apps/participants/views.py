from django.shortcuts import render
from apps.accounts.decorators import module_required
from .models import Participant


@module_required('participant')
def participant_list(request):
    participants = Participant.objects.all()
    q = request.GET.get('q', '')
    if q:
        participants = participants.filter(name__icontains=q)
    return render(request, 'participants/list.html', {'participants': participants, 'q': q})
