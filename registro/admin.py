from django.contrib import admin
from django.http import HttpResponse
from django.db.models import Sum
from django.utils.html import format_html
from django.core.serializers.json import DjangoJSONEncoder
from datetime import date
import csv
import json

# --- IMPORTS PARA PDF (ReportLab) ---
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

from .models import Perfil, Obra, Asistencia, ReporteImproductivo, BalanceObra

# --- ACCIÓN 1: EXPORTAR A CSV (Excel) ---
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
exportar_a_excel.short_description = "📊 Exportar a Excel (CSV)"

# --- ACCIÓN 2: EXPORTAR A PDF (NUEVO) ---
def exportar_a_pdf(modeladmin, request, queryset):
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="reporte_{modeladmin.model._meta.verbose_name_plural}.pdf"'

    # Crear el documento PDF
    doc = SimpleDocTemplate(response, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    # Título del Reporte
    titulo = f"Reporte de {modeladmin.model._meta.verbose_name_plural.title()}"
    elements.append(Paragraph(titulo, styles['Title']))
    elements.append(Spacer(1, 12))

    # Preparar datos para la tabla
    # Obtenemos los nombres de las columnas (verboses names si es posible)
    columns = [field.verbose_name.title() for field in modeladmin.model._meta.fields]
    data = [columns] # Primera fila son los encabezados

    # Llenamos las filas
    for obj in queryset:
        row = []
        for field in modeladmin.model._meta.fields:
            value = getattr(obj, field.name)
            if value is None:
                value = ""
            row.append(str(value)) # Convertir todo a string
        data.append(row)

    # Crear la tabla
    table = Table(data)
    
    # Estilo de la tabla (Bordes, Colores, Encabezado)
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 8), # Letra pequeña para que quepa
    ])
    table.setStyle(style)

    elements.append(table)
    
    # Pie de página
    elements.append(Spacer(1, 24))
    elements.append(Paragraph("Generado por Sistema Subcontractor App", styles['Normal']))

    doc.build(elements)
    return response
exportar_a_pdf.short_description = "📄 Exportar a PDF"


# --- CONFIGURACIÓN DE MODELOS ---

@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'rut', 'rol', 'estado_dispositivo')
    actions = ['resetear_dispositivo'] # Ya tenías esto antes o lo agregamos si falta

    def estado_dispositivo(self, obj):
        if obj.dispositivo_id:
            return format_html('<span style="color: green;">🔒 Vinculado</span>')
        return format_html('<span style="color: orange;">🔓 Sin vincular</span>')
    estado_dispositivo.short_description = "Seguridad Móvil"

    def resetear_dispositivo(self, request, queryset):
        queryset.update(dispositivo_id=None)
        self.message_user(request, "Dispositivos reseteados.")
    resetear_dispositivo.short_description = "🔄 Resetear Celular"

# --- BALANCE DE OBRA ---
@admin.register(BalanceObra)
class BalanceObraAdmin(admin.ModelAdmin):
    list_display = (
        'obra', 
        'barra_progreso', 
        'impacto_multas',
        'proyeccion_final',
        'dias_restantes_vida'   
    )
    list_filter = ('es_rentable', 'obra')
    actions = [exportar_a_excel, exportar_a_pdf] # <--- AGREGADO PDF AQUÍ
    
    # 1. BARRA DE PROGRESO
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

    # 2. IMPACTO MULTAS
    def impacto_multas(self, obj):
        if obj.total_multas_proyectadas > 0:
            return format_html(f'<span style="color: red; font-weight: bold;">-${obj.total_multas_proyectadas:,.0f} (Multas)</span>')
        return format_html('<span style="color: #aaa;">Sin multas</span>')
    impacto_multas.short_description = "Multas Proyectadas"

    # 3. PROYECCIÓN
    def proyeccion_final(self, obj):
        gastado_real_total = obj.total_pagado_sueldos + obj.total_perdido_improductivo + obj.total_multas_proyectadas
        dias_pasados = (date.today() - obj.obra.fecha_inicio).days
        if dias_pasados <= 0: return "Calculando..."

        gasto_operativo_acum = obj.total_pagado_sueldos + obj.total_perdido_improductivo
        gasto_diario_promedio = gasto_operativo_acum / dias_pasados
        
        duracion_total = (obj.obra.fecha_termino_estimada - obj.obra.fecha_inicio).days
        costo_final_proyectado = (gasto_diario_promedio * duracion_total) + obj.total_multas_proyectadas
        
        diferencia = obj.obra.presupuesto_total - costo_final_proyectado
        
        if diferencia >= 0:
            return format_html(f'<span style="color: green; font-weight: bold;">🟢 +${diferencia:,.0f}</span>')
        else:
            return format_html(f'<span style="color: red; font-weight: bold;">🔴 QUIEBRA (-${abs(diferencia):,.0f})</span>')
    proyeccion_final.short_description = "Rentabilidad Final Estimada"

    # 4. SALUD FINANCIERA
    def dias_restantes_vida(self, obj):
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

    # 5. GRÁFICO
    def changelist_view(self, request, extra_context=None):
        balances = BalanceObra.objects.select_related('obra').all()

        chart_data = []
        for b in balances:
            chart_data.append({
                'obra': b.obra.nombre,
                'perdido': float(b.total_perdido_improductivo),
                'multas': float(b.total_multas_proyectadas),
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
    actions = [exportar_a_excel, exportar_a_pdf] # <--- AGREGADO PDF AQUÍ

@admin.register(Asistencia)
class AsistenciaAdmin(admin.ModelAdmin):
    list_display = ('trabajador', 'obra', 'fecha', 'hora_entrada', 'hora_salida', 'audit_info')
    list_filter = ('fecha', 'obra', 'trabajador')
    readonly_fields = ('fecha_modificacion', 'modificado_por')
    actions = [exportar_a_excel, exportar_a_pdf] # <--- AGREGADO PDF AQUÍ

    def audit_info(self, obj):
        if obj.modificado_por:
            return format_html(
                f'<small style="color:#666;">Mod: {obj.modificado_por.username}<br>{obj.fecha_modificacion.strftime("%d/%m %H:%M")}</small>'
            )
        return "-"
    audit_info.short_description = "Auditoría"

    def save_model(self, request, obj, form, change):
        obj.modificado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(ReporteImproductivo)
class ReporteImproductivoAdmin(admin.ModelAdmin):
    list_display = (
        'estado_lectura', 
        'obra', 
        'motivo_corto', 
        'dias_retraso_obra', 
        'dinero_perdido_fmt',
        'fecha'
    )
    list_filter = ('leido', 'fecha', 'obra')
    actions = [exportar_a_excel, exportar_a_pdf, 'marcar_como_leido'] # <--- AGREGADO PDF AQUÍ

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