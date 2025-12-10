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
        elif perfil.rol == 'JEFE':
            return redirect('dashboard_jefe') 
        else:
            return redirect('/admin/')
    except:
        return redirect('/admin/')

# 2. VISTA DEL TRABAJADOR (La App Móvil)
@login_required
@solo_trabajadores
def panel_trabajador(request):
    perfil = request.user.perfil
    hoy = timezone.now().date()
    
    asistencia_activa = Asistencia.objects.filter(
        trabajador=perfil,
        fecha=hoy,
        hora_salida__isnull=True
    ).first()

    if request.method == 'POST':
        lat = request.POST.get('latitud')
        lon = request.POST.get('longitud')
        foto = request.FILES.get('foto')

        if not lat or not lon:
            messages.error(request, "Error: No se pudo obtener tu ubicación GPS.")
            return redirect('panel_trabajador')

        if 'marcar_entrada' in request.POST:
            obra_id = request.POST.get('obra_id')
            obra = get_object_or_404(Obra, id=obra_id)
            
            Asistencia.objects.create(
                trabajador=perfil,
                obra=obra,
                latitud_entrada=lat,
                longitud_entrada=lon,
                foto_entrada=foto
            )
            messages.success(request, "¡Entrada marcada exitosamente!")

        elif 'marcar_salida' in request.POST and asistencia_activa:
            asistencia_activa.hora_salida = timezone.now().time()
            asistencia_activa.latitud_salida = lat
            asistencia_activa.longitud_salida = lon
            
            if foto:
                asistencia_activa.foto_salida = foto
            
            asistencia_activa.save()
            messages.success(request, "¡Salida marcada! Buen descanso.")
            
        return redirect('panel_trabajador')

    obras = Obra.objects.filter(activa=True)
    return render(request, 'trabajador/panel.html', {
        'asistencia_activa': asistencia_activa,
        'obras': obras
    })

# 3. VISTA DEL JEFE DE OBRA (Dashboard Multi-Obra)
@login_required
def dashboard_jefe_obra(request):
    try:
        perfil = request.user.perfil
    except:
        return redirect('admin:index')

    if perfil.rol != 'JEFE':
        return redirect('home') 
    
    # 1. Obtenemos TODAS las obras activas asignadas a este jefe
    mis_obras = Obra.objects.filter(jefe_obra=perfil, activa=True)
    
    if not mis_obras.exists():
        return render(request, 'registro/error_no_obra.html')

    # 2. Lógica de Selección: ¿El usuario eligió una obra específica en el menú?
    obra_id = request.GET.get('obra_id')
    
    if obra_id:
        # Intentamos obtener esa obra específica, validando que sea suya
        obra_actual = get_object_or_404(Obra, id=obra_id, jefe_obra=perfil)
    else:
        # Si no eligió ninguna, mostramos la primera por defecto
        obra_actual = mis_obras.first()

    # 3. Calculamos los datos SOLO para la obra seleccionada ('obra_actual')
    hoy = timezone.now().date()
    asistencias_hoy = Asistencia.objects.filter(obra=obra_actual, fecha=hoy).order_by('-hora_entrada')
    
    presentes = asistencias_hoy.count()
    alertas_gps = asistencias_hoy.filter(entrada_valida=False).count()
    
    context = {
        'obra': obra_actual,      # La obra activa en la vista
        'mis_obras': mis_obras,   # La lista para el menú desplegable
        'asistencias_hoy': asistencias_hoy,
        'presentes': presentes,
        'alertas_gps': alertas_gps,
        'fecha_hoy': hoy,
    }
    return render(request, 'registration/dashboard_jefe.html', context)