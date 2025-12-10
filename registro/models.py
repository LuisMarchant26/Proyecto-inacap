from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
import math

# ... (Perfil se mantiene igual) ...
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
    sueldo_diario = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    valor_hora = models.DecimalField(max_digits=10, decimal_places=0, default=0)

    def __str__(self):
        return f"{self.usuario.get_full_name()} ({self.rol})"

# ... (Modificamos Obra para agregar la MULTA) ...
class Obra(models.Model):
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=255)
    latitud = models.DecimalField(max_digits=9, decimal_places=6) 
    longitud = models.DecimalField(max_digits=9, decimal_places=6)
    radio_permitido = models.IntegerField(default=50)
    
    presupuesto_total = models.DecimalField(max_digits=15, decimal_places=0)
    
    # NUEVO: Valor de la multa por día de atraso (UF o Pesos)
    valor_multa_dia = models.DecimalField(max_digits=10, decimal_places=0, default=0, help_text="Multa por día de atraso según contrato")
    
    fecha_inicio = models.DateField()
    fecha_termino_estimada = models.DateField()
    
    jefe_obra = models.ForeignKey(Perfil, on_delete=models.SET_NULL, null=True, limit_choices_to={'rol': 'JEFE'})
    activa = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

class BalanceObra(models.Model):
    obra = models.ForeignKey(Obra, on_delete=models.CASCADE)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    total_pagado_sueldos = models.DecimalField(max_digits=15, decimal_places=0, default=0)
    total_perdido_improductivo = models.DecimalField(max_digits=15, decimal_places=0, default=0)
    
    # NUEVO: Acumulado de multas proyectadas
    total_multas_proyectadas = models.DecimalField(max_digits=15, decimal_places=0, default=0)
    
    presupuesto_restante = models.DecimalField(max_digits=15, decimal_places=0, default=0)
    es_rentable = models.BooleanField(default=True)

    def actualizar_balance(self):
        pagos = Asistencia.objects.filter(obra=self.obra).aggregate(total=models.Sum('monto_pago_dia'))['total'] or 0
        
        # Sumar dinero perdido operativo (Sueldos tirados a la basura)
        perdidas_op = ReporteImproductivo.objects.filter(obra=self.obra).aggregate(total=models.Sum('dinero_perdido'))['total'] or 0
        
        # NUEVO: Calcular Multas por Atraso (Suma de días reportados * Valor Multa)
        dias_atraso = ReporteImproductivo.objects.filter(obra=self.obra).aggregate(total=models.Sum('dias_retraso_obra'))['total'] or 0
        monto_multas = dias_atraso * self.obra.valor_multa_dia
        
        self.total_pagado_sueldos = pagos
        self.total_perdido_improductivo = perdidas_op
        self.total_multas_proyectadas = monto_multas
        
        # El gasto total ahora incluye la multa potencial
        gastos_totales = pagos + perdidas_op + monto_multas
        self.presupuesto_restante = self.obra.presupuesto_total - gastos_totales
        
        self.es_rentable = self.presupuesto_restante > (self.obra.presupuesto_total * Decimal(0.10))
        self.save()

# ... (Asistencia queda igual) ...
class Asistencia(models.Model):
    trabajador = models.ForeignKey(Perfil, on_delete=models.CASCADE)
    obra = models.ForeignKey(Obra, on_delete=models.CASCADE)
    fecha = models.DateField(default=timezone.now)
    hora_entrada = models.TimeField(auto_now_add=True)
    latitud_entrada = models.DecimalField(max_digits=9, decimal_places=6)
    longitud_entrada = models.DecimalField(max_digits=9, decimal_places=6)
    foto_entrada = models.ImageField(upload_to='asistencias/entrada/', blank=True, null=True)
    entrada_valida = models.BooleanField(default=False)
    hora_salida = models.TimeField(blank=True, null=True)
    latitud_salida = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitud_salida = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    foto_salida = models.ImageField(upload_to='asistencias/salida/', blank=True, null=True)
    horas_trabajadas = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    monto_pago_dia = models.DecimalField(max_digits=10, decimal_places=0, default=0)

    def save(self, *args, **kwargs):
        if not self.hora_entrada:
            self.hora_entrada = timezone.now().time()
        dist_in = self.calcular_distancia(self.obra.latitud, self.obra.longitud, self.latitud_entrada, self.longitud_entrada)
        self.entrada_valida = dist_in <= self.obra.radio_permitido

        if self.hora_salida:
            dt_entrada = timezone.datetime.combine(self.fecha, self.hora_entrada)
            dt_salida = timezone.datetime.combine(self.fecha, self.hora_salida)
            if timezone.is_naive(dt_entrada): dt_entrada = timezone.make_aware(dt_entrada)
            if timezone.is_naive(dt_salida): dt_salida = timezone.make_aware(dt_salida)
            diferencia = dt_salida - dt_entrada
            self.horas_trabajadas = Decimal(diferencia.total_seconds() / 3600)
            if self.horas_trabajadas >= 8:
                 self.monto_pago_dia = self.trabajador.sueldo_diario
            else:
                 self.monto_pago_dia = self.trabajador.valor_hora * self.horas_trabajadas
        super().save(*args, **kwargs)
        balance, created = BalanceObra.objects.get_or_create(obra=self.obra)
        balance.actualizar_balance()

    @staticmethod
    def calcular_distancia(lat1, lon1, lat2, lon2):
        try:
            lat1, lon1 = float(lat1), float(lon1)
            lat2, lon2 = float(lat2), float(lon2)
        except (ValueError, TypeError): return 999999
        R = 6371000 
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c
    
    def __str__(self): return f"{self.fecha} - {self.trabajador}"

# ... (Modificamos ReporteImproductivo para agregar DIAS DE RETRASO) ...
class ReporteImproductivo(models.Model):
    obra = models.ForeignKey(Obra, on_delete=models.CASCADE)
    jefe_obra = models.ForeignKey(Perfil, on_delete=models.SET_NULL, null=True, related_name='reportes_creados')
    fecha = models.DateField(default=timezone.now)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    motivo = models.TextField()
    evidencia_foto = models.ImageField(upload_to='evidencias_perdida/', blank=True, null=True)
    trabajadores_afectados = models.ManyToManyField(Perfil, limit_choices_to={'rol': 'TRABAJADOR'})
    
    # NUEVO: ¿Esto genera atraso en la entrega?
    dias_retraso_obra = models.DecimalField(max_digits=4, decimal_places=1, default=0, help_text="Días que se atrasa la entrega final por este incidente")
    
    horas_perdidas_totales = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    dinero_perdido = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    leido = models.BooleanField(default=False, verbose_name="¿Leído por Admin?")

    def calcular_impacto(self):
        inicio = timezone.datetime.combine(self.fecha, self.hora_inicio)
        fin = timezone.datetime.combine(self.fecha, self.hora_fin)
        duracion_horas = Decimal((fin - inicio).total_seconds() / 3600)
        costo_total = 0
        for trabajador in self.trabajadores_afectados.all():
            costo_total += trabajador.valor_hora * duracion_horas
        self.horas_perdidas_totales = duracion_horas
        self.dinero_perdido = costo_total
        self.save()
        balance, created = BalanceObra.objects.get_or_create(obra=self.obra)
        balance.actualizar_balance()

    def __str__(self): return f"Pérdida: ${self.dinero_perdido} - {self.motivo}"

@receiver(m2m_changed, sender=ReporteImproductivo.trabajadores_afectados.through)
def actualizar_costo_improductivo(sender, instance, action, **kwargs):
    if action in ["post_add", "post_remove", "post_clear"]:
        instance.calcular_impacto()