from django.contrib import admin
from django.http import HttpResponse
import csv
from .models import Perfil, Obra, Asistencia, ReporteImproductivo, BalanceObra

# Acción personalizada para exportar a Excel (CSV)
def exportar_a_excel(modeladmin, request, queryset):
    meta = modeladmin.model._meta
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename={meta}.csv'
    
    writer = csv.writer(response)
    
    # Escribir encabezados
    field_names = [field.name for field in meta.fields]
    writer.writerow(field_names)
    
    # Escribir datos seleccionados
    for obj in queryset:
        writer.writerow([getattr(obj, field) for field in field_names])
        
    return response
exportar_a_excel.short_description = "Exportar seleccionados a Excel"

# 1. Configuración de Asistencia en el Admin
class AsistenciaAdmin(admin.ModelAdmin):
    list_display = ('trabajador', 'obra', 'fecha', 'hora_entrada', 'hora_salida', 'horas_trabajadas', 'monto_pago_dia', 'entrada_valida')
    list_filter = ('fecha', 'obra', 'trabajador') # <-- Aquí está el filtro por FECHA (30 días, mes actual, etc.)
    actions = [exportar_a_excel] # <-- Aquí agregamos el botón de descarga

# 2. Configuración de Reporte de Pérdidas en el Admin
class ReporteImproductivoAdmin(admin.ModelAdmin):
    list_display = ('obra', 'fecha', 'motivo', 'horas_perdidas_totales', 'dinero_perdido')
    list_filter = ('fecha', 'obra') # <-- Filtro para sacar el reporte mensual
    actions = [exportar_a_excel]

# 3. Configuración básica de los otros modelos
admin.site.register(Perfil)
admin.site.register(Obra)
admin.site.register(BalanceObra)
# Registramos los modelos con sus configuraciones avanzadas
admin.site.register(Asistencia, AsistenciaAdmin)
admin.site.register(ReporteImproductivo, ReporteImproductivoAdmin)