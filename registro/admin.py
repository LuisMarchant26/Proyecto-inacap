from django.contrib import admin
from django.http import HttpResponse
from django.db.models import Sum
from django.utils.html import format_html
from django.core.serializers.json import DjangoJSONEncoder
from datetime import date
import csv
import json
from .models import Perfil, Obra, Asistencia, ReporteImproductivo, BalanceObra

# --- ACCIÓN GLOBAL: EXPORTAR A EXCEL ---
def exportar_a_excel(modeladmin, request, queryset):
    meta = modeladmin.model._meta
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename={meta}.csv'
    
    writer = csv.writer(response)
    field_names = [field.name for field in meta.fields]
    writer.writerow(field_names)
    
    for obj in queryset:
        writer.writerow([getattr(obj, field) for field in field_names])
        
    return response
exportar_a_excel.short_description = "Exportar seleccionados a Excel"

# --- CONFIGURACIÓN DE MODELOS ---

admin.site.register(Perfil)

# --- BALANCE DE OBRA: VISIÓN FINANCIERA COMPLETA ---
@admin.register(BalanceObra)
class BalanceObraAdmin(admin.ModelAdmin):
    list_display = (
        'obra', 
        'barra_progreso', 
        'impacto_multas',       # <--- NUEVO: Muestra dinero perdido en multas
        'proyeccion_final',     # <--- NUEVO: Cálculo predictivo (Gasto + Multas)
        'dias_restantes_vida'   
    )
    list_filter = ('es_rentable', 'obra')
    
    # 1. BARRA DE PROGRESO VISUAL
    def barra_progreso(self, obj):
        total = obj.obra.presupuesto_total
        if total == 0: return "0%"
        gastado = total - obj.presupuesto_restante
        porcentaje = (gastado / total) * 100
        
        color = "green"
        if porcentaje > 70: color = "orange"
        if porcentaje > 90: color = "red"
        
        return format_html(
            f'''
            <div style="width: 100px; background: #e9ecef; border-radius: 4px; border: 1px solid #ccc;">
                <div style="width: {porcentaje}%; background: {color}; height: 10px; border-radius: 2px;"></div>
            </div>
            <small style="color: #666;">{porcentaje:.1f}% Gastado</small>
            '''
        )
    barra_progreso.short_description = "% Ejecución"

    # 2. IMPACTO DE MULTAS (CONTRACTUAL)
    def impacto_multas(self, obj):
        if obj.total_multas_proyectadas > 0:
            return format_html(f'<span style="color: red; font-weight: bold;">-${obj.total_multas_proyectadas:,.0f} (Multas)</span>')
        return format_html('<span style="color: #aaa;">Sin multas</span>')
    impacto_multas.short_description = "Multas Proyectadas"

    # 3. PROYECCIÓN FINAL (RENTABILIDAD A LARGO PLAZO)
    def proyeccion_final(self, obj):
        # Gasto Real Total = Operativo + Multas
        gastado_real_total = obj.total_pagado_sueldos + obj.total_perdido_improductivo + obj.total_multas_proyectadas
        
        dias_pasados = (date.today() - obj.obra.fecha_inicio).days
        if dias_pasados <= 0: return "Calculando..."

        # Calculamos solo el gasto operativo diario (las multas son hitos, no promedio diario)
        gasto_operativo_acum = obj.total_pagado_sueldos + obj.total_perdido_improductivo
        gasto_diario_promedio = gasto_operativo_acum / dias_pasados
        
        duracion_total = (obj.obra.fecha_termino_estimada - obj.obra.fecha_inicio).days
        
        # COSTO FINAL = (Gasto Diario * Días Totales) + MULTAS YA ACUMULADAS
        costo_final_proyectado = (gasto_diario_promedio * duracion_total) + obj.total_multas_proyectadas
        
        diferencia = obj.obra.presupuesto_total - costo_final_proyectado
        
        if diferencia >= 0:
            return format_html(f'<span style="color: green; font-weight: bold;">🟢 +${diferencia:,.0f}</span>')
        else:
            return format_html(f'<span style="color: red; font-weight: bold;">🔴 QUIEBRA (-${abs(diferencia):,.0f})</span>')
    proyeccion_final.short_description = "Rentabilidad Final Estimada"

    # 4. SALUD FINANCIERA (LIQUIDEZ)
    def dias_restantes_vida(self, obj):
        # Para saber cuánto dura la caja, usamos el presupuesto restante REAL (ya descontadas las multas)
        caja_disponible = obj.presupuesto_restante
        
        gasto_operativo_acum = obj.total_pagado_sueldos + obj.total_perdido_improductivo
        dias_pasados = (date.today() - obj.obra.fecha_inicio).days
        
        if dias_pasados <= 0 or gasto_operativo_acum <= 0: return "-"
        
        gasto_diario = gasto_operativo_acum / dias_pasados
        
        if gasto_diario > 0:
            dias_vida = caja_disponible / gasto_diario
        else:
            return "Sin gastos"
            
        dias_reales_restantes = (obj.obra.fecha_termino_estimada - date.today()).days
        
        if dias_vida < dias_reales_restantes:
             return format_html(f'<span style="color: red; font-weight: bold;">⚠️ Fondos para {dias_vida:.0f} días</span>')
        
        return f"Cubierto ({dias_vida:.0f} días)"
    dias_restantes_vida.short_description = "Salud de Caja"

    # 5. GRÁFICO ACTUALIZADO CON MULTAS
    def changelist_view(self, request, extra_context=None):
        balances = BalanceObra.objects.select_related('obra').all()

        chart_data = []
        for b in balances:
            chart_data.append({
                'obra': b.obra.nombre,
                'perdido': float(b.total_perdido_improductivo),
                'multas': float(b.total_multas_proyectadas), # Nueva barra para multas
                'sueldos': float(b.total_pagado_sueldos),
                'restante': float(b.presupuesto_restante)
            })

        extra_context = extra_context or {}
        extra_context['chart_data'] = json.dumps(chart_data, cls=DjangoJSONEncoder)

        return super().changelist_view(request, extra_context=extra_context)


@admin.register(Obra)
class ObraAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'direccion', 'jefe_obra', 'valor_multa_dia', 'presupuesto_total')
    search_fields = ('nombre', 'direccion')
    list_filter = ('activa',)

@admin.register(Asistencia)
class AsistenciaAdmin(admin.ModelAdmin):
    list_display = ('trabajador', 'obra', 'fecha', 'hora_entrada', 'hora_salida', 'horas_trabajadas', 'monto_pago_dia', 'entrada_valida')
    list_filter = ('fecha', 'obra', 'trabajador')
    actions = [exportar_a_excel]

@admin.register(ReporteImproductivo)
class ReporteImproductivoAdmin(admin.ModelAdmin):
    list_display = (
        'estado_lectura', 
        'obra', 
        'motivo_corto', 
        'dias_retraso_obra', # <--- NUEVO: Muestra días de atraso en la lista
        'dinero_perdido_fmt',
        'fecha'
    )
    list_filter = ('leido', 'fecha', 'obra')
    actions = [exportar_a_excel, 'marcar_como_leido']

    def estado_lectura(self, obj):
        if not obj.leido:
            return format_html('<span style="color: red; font-weight: bold;">🔴 NUEVO</span>')
        return format_html('<span style="color: green;">✅ Leído</span>')
    estado_lectura.short_description = "Estado"

    def dinero_perdido_fmt(self, obj):
        return f"${obj.dinero_perdido:,.0f}"
    dinero_perdido_fmt.short_description = "Costo Operativo"

    def motivo_corto(self, obj):
        return obj.motivo[:40] + "..." if len(obj.motivo) > 40 else obj.motivo
    motivo_corto.short_description = "Motivo"

    def marcar_como_leido(self, request, queryset):
        queryset.update(leido=True)
        self.message_user(request, "Reportes marcados como leídos.")
    marcar_como_leido.short_description = "Marcar seleccionados como Leídos"

    def changelist_view(self, request, extra_context=None):
        resumen = ReporteImproductivo.objects.values('obra__nombre').annotate(
            total=Sum('dinero_perdido')
        ).order_by('-total')

        chart_data = [
            {'obra': item['obra__nombre'], 'total': float(item['total'])} 
            for item in resumen
        ]

        extra_context = extra_context or {}
        extra_context['chart_data'] = json.dumps(chart_data, cls=DjangoJSONEncoder)

        return super().changelist_view(request, extra_context=extra_context)