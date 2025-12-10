from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import Obra, Asistencia
from .serializers import ObraSerializer

# 1. ENCHUFE PARA QUE LA APK DESCARGUE LAS OBRAS
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def lista_obras(request):
    obras = Obra.objects.filter(activa=True)
    serializer = ObraSerializer(obras, many=True)
    return Response(serializer.data)

# 2. ENCHUFE PARA QUE LA APK MARQUE ASISTENCIA
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def marcar_asistencia_api(request):
    try:
        perfil = request.user.perfil
    except:
        return Response({"error": "Usuario no es trabajador"}, status=400)
    
    # Recibimos datos JSON o Form-Data desde la APK
    obra_id = request.data.get('obra_id')
    lat = request.data.get('latitud')
    lon = request.data.get('longitud')
    foto = request.FILES.get('foto') # La foto viene como archivo

    if not all([obra_id, lat, lon]):
        return Response({"error": "Faltan datos (Obra o GPS)"}, status=400)

    obra = get_object_or_404(Obra, id=obra_id)

    # Revisar si es Entrada o Salida
    asistencia_activa = Asistencia.objects.filter(
        trabajador=perfil, 
        fecha=timezone.now().date(), 
        hora_salida__isnull=True
    ).first()

    if asistencia_activa:
        # ES SALIDA
        asistencia_activa.hora_salida = timezone.now().time()
        asistencia_activa.latitud_salida = lat
        asistencia_activa.longitud_salida = lon
        if foto:
            asistencia_activa.foto_salida = foto
        asistencia_activa.save()
        return Response({"mensaje": "SALIDA marcada correctamente", "estado": "salida"})
    else:
        # ES ENTRADA
        Asistencia.objects.create(
            trabajador=perfil,
            obra=obra,
            latitud_entrada=lat,
            longitud_entrada=lon,
            foto_entrada=foto
        )
        return Response({"mensaje": "ENTRADA marcada correctamente", "estado": "entrada"}, status=201)