from django.contrib import admin
from django.urls import path, include  # <--- IMPORTANTE: Agrega 'include'
from django.conf import settings
from django.conf.urls.static import static
from registro import views


urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Rutas de autenticación estándar (Login, Logout, Password Reset)
    path('accounts/', include('django.contrib.auth.urls')), 
    
    path('', views.home, name='home'),
    path('trabajador/', views.panel_trabajador, name='panel_trabajador'),
    path('dashboard-jefe/', views.dashboard_jefe_obra, name='dashboard_jefe'),
    path('v1/', include('registro.urls')), # Endpoint REST API
    path('jefe/reportar/', views.crear_reporte, name='crear_reporte'),
    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)