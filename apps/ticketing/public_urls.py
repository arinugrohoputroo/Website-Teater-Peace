from django.urls import path
from . import public_views

app_name = 'public_order'

urlpatterns = [
    path('', public_views.ticket_select, name='ticket_select'),
    path('checkout/', public_views.checkout, name='checkout'),
    path('confirmation/<str:order_number>/', public_views.order_confirm, name='order_confirm'),
    path('upload-proof/<str:order_number>/', public_views.upload_proof, name='upload_proof'),
    path('receipt/<str:order_number>/', public_views.order_receipt, name='receipt'),
    path('status/', public_views.order_status, name='order_status'),
    path('status/<str:order_number>/', public_views.order_detail, name='order_detail'),
]
