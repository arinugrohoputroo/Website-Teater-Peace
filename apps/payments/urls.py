from django.urls import path

from . import views

app_name = 'payments'
urlpatterns = [
    path('', views.payment_list, name='list'),
    path('methods/', views.payment_method_list, name='methods'),
    path('methods/add/', views.payment_method_add, name='method_add'),
    path('methods/<int:pk>/edit/', views.payment_method_edit, name='method_edit'),
    path('methods/<int:pk>/toggle/', views.payment_method_toggle, name='method_toggle'),
    path('methods/<int:pk>/delete/', views.payment_method_delete, name='method_delete'),
    path('<int:pk>/verify/', views.payment_verify, name='verify'),
    path('<int:pk>/approve/', views.payment_approve, name='approve'),
    path('<int:pk>/reject/', views.payment_reject, name='reject'),
]
