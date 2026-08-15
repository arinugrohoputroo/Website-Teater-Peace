from django.urls import path
from . import views

app_name = 'participants'

urlpatterns = [
    path('', views.participant_list, name='list'),
]
