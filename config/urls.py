from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('', RedirectView.as_view(url='/accounts/login/', permanent=False)),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('patient/', include('patients.urls', namespace='patients')),
    path('doctor/', include('doctors.urls', namespace='doctors')),
    path('staff/', include('staff.urls', namespace='staff')),
    path('admin-panel/', include('administration.urls', namespace='administration')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
