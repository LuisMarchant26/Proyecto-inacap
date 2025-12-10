from django.urls import path
from . import api

urlpatterns = [
    # Rutas para la App Móvil
    path('api/obras/', api.lista_obras, name='api_obras'),
    path('api/marcar/', api.marcar_asistencia_api, name='api_marcar'),
]