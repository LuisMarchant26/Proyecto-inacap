from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
import math

# 1. PERFILES (Con datos económicos para calcular pagos y pérdidas)
class Perfil(models.Model):
    ROLES = [
        ('ADMIN', 'Administrador'),
        ('JEFE', 'Jefe de Obra'),
        ('TRABAJADOR', 'Trabajador'),
    ]
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    rut = models.CharField(max_length=12, unique=True)
    rol = models.CharField(max_length=20, choices=ROLES, default='TRABAJADOR')
    telefono = models.CharField(max_length=15, blank=True, null=True)
    
    # Datos económicos CRÍTICOS para el requerimiento de "Calcular pagos y pérdidas" 
    sueldo_diario = models.DecimalField(max_digits=10, decimal_places=0, default=0, help_text="Costo diario del trabajador para la empresa")
    valor_hora = models.DecimalField(max_digits=10, decimal_places=0, default=0, help_text="Para calcular pérdidas por horas improductivas")

    def __str__(self):
        return f"{self.usuario.get_full_name()} ({self.rol})"

# 2. OBRA (Con datos para proyección de rentabilidad) 
class Obra(models.Model):
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=255)
    
    # Geocerca para validar asistencia GPS
    latitud = models.DecimalField(max_digits=9, decimal_places=6) 
    longitud = models.DecimalField(max_digits=9, decimal_places=6)
    radio_permitido = models.IntegerField(default=50, help_text="Metros permitidos para marcar")
    
    # Datos Financieros para "Visualizar rentabilidad" [cite: 90]
    presupuesto_total = models.DecimalField(max_digits=15, decimal_places=0)
    fecha_inicio = models.DateField()
    fecha_termino_estimada = models.DateField()
    
    jefe_obra = models.ForeignKey(Perfil, on_delete=models.SET_NULL, null=True, limit_choices_to={'rol': 'JEFE'})
    activa = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

# 3. ASISTENCIA (GPS + Foto - Reemplaza al QR solicitado en HU01) 
class Asistencia(models.Model):
    trabajador = models.ForeignKey(Perfil, on_delete=models.CASCADE)
    obra = models.ForeignKey(Obra, on_delete=models.CASCADE)
    fecha = models.DateField(default=timezone.now)
    
    # ENTRADA
    hora_entrada = models.TimeField(auto_now_add=True)
    latitud_entrada = models.DecimalField(max_digits=9, decimal_places=6)
    longitud_entrada = models.DecimalField(max_digits=9, decimal_places=6)
    foto_entrada = models.ImageField(upload_to='asistencias/entrada/', blank=True, null=True)
    entrada_valida = models.BooleanField(default=False)

    # SALIDA
    hora_salida = models.TimeField(blank=True, null=True)
    latitud_salida = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitud_salida = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    foto_salida = models.ImageField(upload_to='asistencias/salida/', blank=True, null=True)
    
    # Cálculos automáticos
    horas_trabajadas = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    monto_pago_dia = models.DecimalField(max_digits=10, decimal_places=0, default=0)

    def save(self, *args, **kwargs):
        # 1. Validación Geográfica (GPS)
        dist_in = self.calcular_distancia(self.obra.latitud, self.obra.longitud, self.latitud_entrada, self.longitud_entrada)
        self.entrada_valida = dist_in <= self.obra.radio_permitido

        # 2. Cálculo de horas y pago al marcar salida
        if self.hora_salida:
            # Lógica simple de diferencia de horas (se puede refinar)
            entrada = timezone.datetime.combine(self.fecha, self.hora_entrada)
            salida = timezone.datetime.combine(self.fecha, self.hora_salida)
            diferencia = salida - entrada
            self.horas_trabajadas = Decimal(diferencia.total_seconds() / 3600)
            
            # Cálculo automático de pago diario 
            # Si trabajó la jornada completa (ej 8 horas) se paga el día, sino proporcional
            if self.horas_trabajadas >= 8:
                 self.monto_pago_dia = self.trabajador.sueldo_diario
            else:
                 self.monto_pago_dia = self.trabajador.valor_hora * self.horas_trabajadas

        super().save(*args, **kwargs)

    @staticmethod
    def calcular_distancia(lat1, lon1, lat2, lon2):
        # Fórmula de Haversine para GPS
        R = 6371000 
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def __str__(self):
        return f"{self.fecha} - {self.trabajador}"

# 4. PÉRDIDAS / TIEMPO IMPRODUCTIVO (El corazón del problema del negocio) 
class ReporteImproductivo(models.Model):
    """
    Registra cuando los trabajadores están presentes pero no pueden trabajar 
    por culpa de la constructora (falta de material, frente no disponible, etc).
    """
    obra = models.ForeignKey(Obra, on_delete=models.CASCADE)
    jefe_obra = models.ForeignKey(Perfil, on_delete=models.SET_NULL, null=True, related_name='reportes_creados')
    fecha = models.DateField(default=timezone.now)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    
    motivo = models.TextField(help_text="Ej: Constructora no liberó losas, falta de grúa, etc.")
    evidencia_foto = models.ImageField(upload_to='evidencias_perdida/', blank=True, null=True)
    
    # Trabajadores afectados (Para calcular cuánto dinero se pierde en sueldos)
    trabajadores_afectados = models.ManyToManyField(Perfil, limit_choices_to={'rol': 'TRABAJADOR'})
    
    # Resultado calculado
    horas_perdidas_totales = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    dinero_perdido = models.DecimalField(max_digits=12, decimal_places=0, default=0)

    def calcular_impacto(self):
        """Calcula automáticamente cuánto dinero pierde la empresa por este evento"""
        # 1. Calcular duración del evento
        inicio = timezone.datetime.combine(self.fecha, self.hora_inicio)
        fin = timezone.datetime.combine(self.fecha, self.hora_fin)
        duracion_horas = Decimal((fin - inicio).total_seconds() / 3600)
        
        costo_total = 0
        # 2. Sumar el costo por hora de cada trabajador detenido
        for trabajador in self.trabajadores_afectados.all():
            costo_total += trabajador.valor_hora * duracion_horas
            
        self.horas_perdidas_totales = duracion_horas
        self.dinero_perdido = costo_total
        self.save()

    def __str__(self):
        return f"Pérdida: ${self.dinero_perdido} - {self.motivo}"

# 5. RENTABILIDAD DEL CONTRATO 
class BalanceObra(models.Model):
    obra = models.ForeignKey(Obra, on_delete=models.CASCADE)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    total_pagado_sueldos = models.DecimalField(max_digits=15, decimal_places=0, default=0)
    total_perdido_improductivo = models.DecimalField(max_digits=15, decimal_places=0, default=0)
    
    # Proyección
    presupuesto_restante = models.DecimalField(max_digits=15, decimal_places=0, default=0)
    es_rentable = models.BooleanField(default=True)

    def actualizar_balance(self):
        # Sumar todos los pagos de asistencia
        pagos = Asistencia.objects.filter(obra=self.obra).aggregate(total=models.Sum('monto_pago_dia'))['total'] or 0
        
        # Sumar todas las pérdidas por improductividad
        perdidas = ReporteImproductivo.objects.filter(obra=self.obra).aggregate(total=models.Sum('dinero_perdido'))['total'] or 0
        
        self.total_pagado_sueldos = pagos
        self.total_perdido_improductivo = perdidas
        
        gastos_totales = pagos + perdidas # + materiales (si existieran)
        self.presupuesto_restante = self.obra.presupuesto_total - gastos_totales
        
        # Definir punto de no rentabilidad (si gasta más del 90% del presupuesto, alerta)
        self.es_rentable = self.presupuesto_restante > (self.obra.presupuesto_total * Decimal(0.10))
        self.save()