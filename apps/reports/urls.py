from django.urls import path

from . import views

app_name = 'reports'
urlpatterns = [
    path('', views.index, name='index'),
    path('sales.csv', views.sales_csv, name='sales_csv'),
    path('not-collected.csv', views.not_collected_csv, name='not_collected_csv'),
]
