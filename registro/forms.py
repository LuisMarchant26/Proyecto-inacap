from django import forms
from .models import ReporteImproductivo, Perfil

class ReporteIncidenteForm(forms.ModelForm):
    class Meta:
        model = ReporteImproductivo
        fields = [
            'hora_inicio', 'hora_fin', 'motivo', 
            'dias_retraso_obra', 'evidencia_foto', 
            'trabajadores_afectados'
        ]
        widgets = {
            'hora_inicio': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'hora_fin': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'motivo': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describe qué pasó...'}),
            'dias_retraso_obra': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'evidencia_foto': forms.FileInput(attrs={'class': 'form-control'}),
            'trabajadores_afectados': forms.SelectMultiple(attrs={'class': 'form-control', 'style': 'height: 150px;'}),
        }
        labels = {
            'dias_retraso_obra': 'Impacto en Entrega (Días)',
            'trabajadores_afectados': 'Selecciona Trabajadores Detenidos (Ctrl + Click para varios)'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtramos para que solo aparezcan TRABAJADORES en la lista (no otros jefes)
        self.fields['trabajadores_afectados'].queryset = Perfil.objects.filter(rol='TRABAJADOR')