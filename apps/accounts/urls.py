from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('profile/', views.profile, name='profile'),
    path('staff/', views.staff_list, name='staff_list'),
    path('staff/add/', views.staff_add, name='staff_add'),
    path('staff/<int:pk>/edit/', views.staff_edit, name='staff_edit'),
    path('staff/<int:pk>/permissions/', views.staff_permissions, name='staff_permissions'),
    path('staff/<int:pk>/toggle/', views.staff_toggle, name='staff_toggle'),
    path('staff/<int:pk>/delete/', views.staff_delete, name='staff_delete'),
    path('staff/<int:pk>/reset-password/', views.staff_reset_password, name='staff_reset_password'),
    path('google-callback/', views.google_login_callback, name='google_callback'),
]
