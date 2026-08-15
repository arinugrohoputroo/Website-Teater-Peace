from django.urls import path

from . import views

app_name = 'snacks'
urlpatterns = [
    path('', views.session_list, name='list'),
    path('scanner/', views.scanner, name='scanner'),
    path('scanner/process/', views.scanner_process, name='scanner_process'),
    path('api/scan/', views.scanner_process, name='api_scan'),
    path('history/', views.history, name='history'),
    path('claims/<int:pk>/delete/', views.claim_delete, name='claim_delete'),
    path('scan/', views.scan_claim, name='scan'),
    path('committee/', views.committee_list, name='committee_list'),
    path('committee/add/', views.committee_add, name='committee_add'),
    path('committee/<int:pk>/edit/', views.committee_edit, name='committee_edit'),
    path('committee/<int:pk>/toggle/', views.committee_toggle, name='committee_toggle'),
    path('committee/<int:pk>/delete/', views.committee_delete, name='committee_delete'),
    path('committee/qr/', views.committee_qr_list, name='committee_qr_list'),
    path('committee/qr/print/', views.committee_qr_print, name='committee_qr_print'),
    path('committee/<int:pk>/', views.committee_detail, name='committee_detail'),
    path('committee/<int:pk>/regenerate-qr/', views.committee_regenerate_qr, name='committee_regenerate_qr'),
    path('committee/<int:pk>/qr.png', views.committee_qr_download, name='committee_qr_download'),
    path('sessions/add/', views.session_add, name='session_add'),
    path('sessions/<int:pk>/edit/', views.session_edit, name='session_edit'),
    path('sessions/<int:pk>/toggle/', views.session_toggle, name='session_toggle'),
    path('sessions/<int:pk>/delete/', views.session_delete, name='session_delete'),
]
