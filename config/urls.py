from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

from apps.accounts import views as account_views
from apps.dashboard import views as dashboard_views
from apps.ticketing import public_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', account_views.login_view, name='login'),
    path('logout/', account_views.logout_view, name='logout'),
    path('accounts/', include('apps.accounts.urls')),
    path('dashboard/', include('apps.dashboard.urls')),
    path('admin-panel/', dashboard_views.index, name='admin_panel'),
    path('staff-panel/', dashboard_views.index, name='staff_panel'),
    path('participants/', include('apps.participants.urls')),
    path('ticketing/', include('apps.ticketing.urls')),
    path('ticket-collection/', include(('apps.ticketing.collection_urls', 'ticket_collection'))),
    path('payments/', include('apps.payments.urls')),
    path('snacks/', include('apps.snacks.urls')),
    path('scanner/', include('apps.scanner.urls')),
    path('reports/', include('apps.reports.urls')),
    path('order/', include('apps.ticketing.public_urls')),
    path('tickets/', public_views.ticket_select, name='tickets'),
    path('', include('apps.core.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
