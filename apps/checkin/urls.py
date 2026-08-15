from django.urls import path

from . import views

app_name = 'checkin'
urlpatterns = [
    path('', views.checkin_scan, name='scan'),
    path('history/', views.checkin_history, name='history'),
]
