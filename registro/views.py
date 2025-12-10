from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from .models import Asistencia, Obra, Perfil, ReporteImproductivo
from .decorators import solo_trabajadores
from .forms import ReporteIncidenteForm  # <--- NUEVO: Importamos el formulario
import uuid  # <--- IMPORTANTE: Para generar el ID único del celular

# --- FUNCIÓN AUXILIAR PARA OBTENER LA IP REAL ---
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

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

# 2. VISTA DEL TRABAJADOR (Con Seguridad Anti-Fraude)
@login_required
@solo_trabajadores
def panel_trabajador(request):
    perfil = request.user.perfil
    
    # --- INICIO: BLOQUEO DE DISPOSITIVO (DEVICE BINDING) ---
    cookie_device = request.COOKIES.get('dispositivo_seguro')
    
    # CASO A: El trabajador NUNCA ha registrado un celular. Lo vinculamos ahora.
    if not perfil.dispositivo_id:
        if not cookie_device:
            # Generamos una huella nueva
            nuevo_id = str(uuid.uuid4())
            perfil.dispositivo_id = nuevo_id
            perfil.save()
            
            # Recargamos la página para guardar la cookie en el navegador
            response = redirect('panel_trabajador')
            # La cookie dura 1 año (365 días)
            response.set_cookie('dispositivo_seguro', nuevo_id, max_age=31536000)
            messages.info(request, "✅ Celular vinculado exitosamente a tu cuenta.")
            return response
            
    # CASO B: Ya tiene un celular registrado. Verificamos si es ESTE.
    else:
        if cookie_device != perfil.dispositivo_id:
            # ¡ALERTA! Intento de acceso desde otro celular (o navegador diferente)
            messages.error(request, "⛔ ERROR DE SEGURIDAD: Esta cuenta está vinculada a otro dispositivo.")
            # Renderizamos la pantalla de bloqueo (asegúrate de que existe este HTML)
            return render(request, 'registration/bloqueo_seguridad.html')

    # --- FIN SEGURIDAD ---

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
        
        # Capturamos la IP para auditoría
        ip_cliente = get_client_ip(request)

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
                foto_entrada=foto,
                ip_registro=ip_cliente  # <--- Guardamos la IP aquí
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
    # Asegúrate que la ruta del template sea correcta ('registration' o 'trabajador')
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
    
    mis_obras = Obra.objects.filter(jefe_obra=perfil, activa=True)
    
    if not mis_obras.exists():
        return render(request, 'registration/error_no_obra.html')

    obra_id = request.GET.get('obra_id')
    
    if obra_id:
        obra_actual = get_object_or_404(Obra, id=obra_id, jefe_obra=perfil)
    else:
        obra_actual = mis_obras.first()

    hoy = timezone.now().date()
    asistencias_hoy = Asistencia.objects.filter(obra=obra_actual, fecha=hoy).order_by('-hora_entrada')
    
    presentes = asistencias_hoy.count()
    alertas_gps = asistencias_hoy.filter(entrada_valida=False).count()
    
    context = {
        'obra': obra_actual,
        'mis_obras': mis_obras,
        'asistencias_hoy': asistencias_hoy,
        'presentes': presentes,
        'alertas_gps': alertas_gps,
        'fecha_hoy': hoy,
    }
    return render(request, 'registration/dashboard_jefe.html', context)

# 4. CREAR REPORTE DE INCIDENTE (Nueva Funcionalidad)
@login_required
def crear_reporte(request):
    try:
        perfil = request.user.perfil
        if perfil.rol != 'JEFE': return redirect('home')
    except:
        return redirect('admin:index')

    # Buscamos la obra activa del jefe (o la seleccionada en la URL)
    obra_id = request.GET.get('obra_id')
    if obra_id:
        obra_actual = get_object_or_404(Obra, id=obra_id, jefe_obra=perfil)
    else:
        # Por defecto tomamos la primera si no se seleccionó
        obra_actual = Obra.objects.filter(jefe_obra=perfil, activa=True).first()

    if not obra_actual:
        messages.error(request, "No tienes una obra activa asignada para reportar incidentes.")
        return redirect('dashboard_jefe')

    if request.method == 'POST':
        form = ReporteIncidenteForm(request.POST, request.FILES)
        if form.is_valid():
            reporte = form.save(commit=False)
            reporte.obra = obra_actual      # Asignación automática
            reporte.jefe_obra = perfil      # Asignación automática
            reporte.save()                  # Guardamos primero para tener ID
            
            form.save_m2m()                 # Guardamos los trabajadores afectados (Many-to-Many)
            
            # Forzamos el cálculo de dinero perdido
            reporte.calcular_impacto() 
            
            messages.success(request, "⚠ Incidente reportado. El impacto financiero se ha calculado.")
            return redirect('dashboard_jefe')
    else:
        form = ReporteIncidenteForm()

    return render(request, 'registration/crear_reporte.html', {'form': form, 'obra': obra_actual})