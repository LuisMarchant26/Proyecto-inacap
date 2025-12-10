from rest_framework import serializers
from .models import Obra, Asistencia

# Traduce las Obras para que la App las muestre en una lista
class ObraSerializer(serializers.ModelSerializer):
    class Meta:
        model = Obra
        fields = ['id', 'nombre', 'direccion', 'latitud', 'longitud', 'radio_permitido']

# Traduce el envío de asistencia (lo que la app nos manda)
class AsistenciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asistencia
        fields = ['obra', 'latitud_entrada', 'longitud_entrada', 'foto_entrada']