from django.urls import path

from . import views

app_name = 'ticket_collection'

urlpatterns = [
    path('', views.ticket_collection, name='index'),
]
