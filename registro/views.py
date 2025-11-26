from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from .models import Asistencia, Obra, Perfil
from .decorators import solo_trabajadores

# 1. EL DIRECTOR DE TRÁFICO (Home)
@login_required
def home(request):
    try:
        perfil = request.user.perfil
        if perfil.rol == 'TRABAJADOR':
            return redirect('panel_trabajador')
        else:
            # Si es Jefe o Admin, lo mandamos directo al panel de reportes de Django
            return redirect('/admin/')
    except:
        return redirect('/admin/') # Fallback por si no tiene perfil

# 2. VISTA DEL TRABAJADOR (La App Móvil)
@login_required
@solo_trabajadores
def panel_trabajador(request):
    perfil = request.user.perfil
    hoy = timezone.now().date()
    
    # Buscamos si ya marcó entrada hoy pero NO ha marcado salida
    asistencia_activa = Asistencia.objects.filter(
        trabajador=perfil,
        fecha=hoy,
        hora_salida__isnull=True
    ).first()

    if request.method == 'POST':
        lat = request.POST.get('latitud')
        lon = request.POST.get('longitud')
        foto = request.FILES.get('foto') # Capturamos la foto

        if not lat or not lon:
            messages.error(request, "Error: No se pudo obtener tu ubicación GPS.")
            return redirect('panel_trabajador')

        # LÓGICA DE ENTRADA
        if 'marcar_entrada' in request.POST:
            # Seleccionamos la obra
            obra_id = request.POST.get('obra_id')
            obra = get_object_or_404(Obra, id=obra_id)
            
            Asistencia.objects.create(
                trabajador=perfil,
                obra=obra,
                latitud_entrada=lat,
                longitud_entrada=lon,
                foto_entrada=foto  # <--- AGREGADO: Guarda la selfie de entrada
            )
            messages.success(request, "¡Entrada marcada exitosamente!")

        # LÓGICA DE SALIDA
        elif 'marcar_salida' in request.POST and asistencia_activa:
            asistencia_activa.hora_salida = timezone.now().time()
            asistencia_activa.latitud_salida = lat
            asistencia_activa.longitud_salida = lon
            
            if foto: # Validamos que venga la foto antes de asignarla
                asistencia_activa.foto_salida = foto # <--- AGREGADO: Guarda la selfie de salida
            
            asistencia_activa.save() # Aquí el modelo calcula el pago automáticamente
            messages.success(request, "¡Salida marcada! Buen descanso.")
            
        return redirect('panel_trabajador')

    # Si es GET (Carga la página), mandamos las obras disponibles
    obras = Obra.objects.filter(activa=True)
    return render(request, 'trabajador/panel.html', {
        'asistencia_activa': asistencia_activa,
        'obras': obras
    })