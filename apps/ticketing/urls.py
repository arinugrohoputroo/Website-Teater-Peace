from django.urls import path

from . import views

app_name = 'ticketing'

urlpatterns = [
    path('', views.order_list, name='list'),
    path('orders/<str:order_number>/', views.order_detail, name='order_detail'),
    path('orders/<str:order_number>/delete/', views.order_delete, name='order_delete'),
    path('offline-sale/', views.offline_sale, name='offline_sale'),
    path('available-ids/', views.available_ticket_ids_api, name='available_ids_api'),
    path('tickets/', views.ticket_list, name='tickets'),
    path('tickets/<str:ticket_number>/', views.ticket_detail, name='ticket_detail'),
    path('collection/', views.ticket_collection, name='collection'),
    path('ticket-types/', views.ticket_type_list, name='ticket_types'),
    path('ticket-types/add/', views.ticket_type_add, name='ticket_type_add'),
    path('ticket-types/<int:pk>/edit/', views.ticket_type_edit, name='ticket_type_edit'),
    path('ticket-types/<int:pk>/toggle/', views.ticket_type_toggle, name='ticket_type_toggle'),
    path('ticket-types/<int:pk>/delete/', views.ticket_type_delete, name='ticket_type_delete'),

    # Naskah management
    path('naskah/', views.naskah_list, name='naskah_list'),
    path('naskah/add/', views.naskah_add, name='naskah_add'),
    path('naskah/<int:pk>/edit/', views.naskah_edit, name='naskah_edit'),
    path('naskah/<int:pk>/delete/', views.naskah_delete, name='naskah_delete'),
]
