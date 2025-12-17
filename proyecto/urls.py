from django.contrib import admin
from django.urls import path, include, re_path  # <--- AGREGADO: re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve           # <--- AGREGADO: serve
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

# --- BLOQUE PARA CARGAR FOTOS EN RENDER Y LOCAL ---
# Esto reemplaza al 'if settings.DEBUG' y fuerza a Django a mostrar 
# las fotos aunque estemos en modo producción.
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {
        'document_root': settings.MEDIA_ROOT,
    }),
]