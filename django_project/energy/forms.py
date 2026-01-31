"""
Forms for the Electric Assistant MVP.
"""

from django import forms
from django.core.exceptions import ValidationError
from .models import Bill, Survey


class BillForm(forms.ModelForm):
    """Formulario para datos del recibo de CFE."""
    
    class Meta:
        model = Bill
        fields = [
            'tarifa', 'periodo_inicio', 'periodo_fin', 'consumo_kwh',
            'total_recibo_mxn', 'lectura_anterior', 'lectura_actual',
            'multiplicador', 'subsidio_mxn', 'evidencia_archivo'
        ]
        widgets = {
            'tarifa': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500'
            }),
            'periodo_inicio': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500'
            }),
            'periodo_fin': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500'
            }),
            'consumo_kwh': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500',
                'placeholder': 'Ej: 280',
                'min': 1,
                'max': 5000
            }),
            'total_recibo_mxn': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500',
                'placeholder': 'Ej: 450.00',
                'step': '0.01'
            }),
            'lectura_anterior': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500',
                'placeholder': 'Opcional'
            }),
            'lectura_actual': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500',
                'placeholder': 'Opcional'
            }),
            'multiplicador': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500',
                'value': 1
            }),
            'subsidio_mxn': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500',
                'placeholder': 'Opcional',
                'step': '0.01'
            }),
            'evidencia_archivo': forms.FileInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500',
                'accept': '.pdf,.jpg,.jpeg,.png'
            }),
        }
        labels = {
            'tarifa': 'Tarifa CFE',
            'periodo_inicio': 'Inicio del periodo',
            'periodo_fin': 'Fin del periodo',
            'consumo_kwh': 'Consumo (kWh)',
            'total_recibo_mxn': 'Total del recibo (MXN) - Opcional',
            'lectura_anterior': 'Lectura anterior - Opcional',
            'lectura_actual': 'Lectura actual - Opcional',
            'multiplicador': 'Multiplicador del medidor',
            'subsidio_mxn': 'Subsidio (MXN) - Opcional',
            'evidencia_archivo': 'Subir recibo (PDF/imagen) - Opcional',
        }
    
    def clean(self):
        cleaned_data = super().clean()
        periodo_inicio = cleaned_data.get('periodo_inicio')
        periodo_fin = cleaned_data.get('periodo_fin')
        consumo_kwh = cleaned_data.get('consumo_kwh')
        lectura_anterior = cleaned_data.get('lectura_anterior')
        lectura_actual = cleaned_data.get('lectura_actual')
        multiplicador = cleaned_data.get('multiplicador', 1) or 1
        
        # Validar que periodo_fin > periodo_inicio
        if periodo_inicio and periodo_fin:
            if periodo_fin <= periodo_inicio:
                raise ValidationError(
                    'La fecha de fin debe ser posterior a la fecha de inicio.'
                )
        
        # Validar lecturas vs consumo (si se proporcionan)
        if lectura_anterior is not None and lectura_actual is not None and consumo_kwh:
            consumo_calculado = (lectura_actual - lectura_anterior) * multiplicador
            tolerancia = consumo_kwh * 0.10  # 10% de tolerancia
            
            if abs(consumo_calculado - consumo_kwh) > tolerancia:
                self.add_error(None, 
                    f'Las lecturas ({consumo_calculado} kWh calculado) no coinciden '
                    f'con el consumo declarado ({consumo_kwh} kWh). '
                    f'Diferencia mayor al 10%. Revisa los datos o deja las lecturas vacías.'
                )
        
        return cleaned_data


class SurveyForm(forms.ModelForm):
    """Formulario del cuestionario de hogar."""
    
    class Meta:
        model = Survey
        exclude = ['bill']
        widgets = {
            'personas_en_casa': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500',
                'min': 1,
                'max': 15
            }),
            'cuartos': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500',
                'min': 1,
                'max': 20
            }),
            'ac_count': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500',
                'hx-trigger': 'change',
                'hx-get': '',  # Se configura en template
                'hx-target': '#ac-hours-container'
            }),
            'ac_horas_dia': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500',
                'min': 0,
                'max': 24
            }),
            'refrigeradores': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500'
            }),
            'ref_antiguedad': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500'
            }),
            'agua_caliente': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500'
            }),
            'lavadora': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-green-600 border-gray-300 rounded focus:ring-green-500'
            }),
            'secadora': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-green-600 border-gray-300 rounded focus:ring-green-500'
            }),
            'home_office': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-green-600 border-gray-300 rounded focus:ring-green-500'
            }),
            'bombeo_agua': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-green-600 border-gray-300 rounded focus:ring-green-500'
            }),
        }
        labels = {
            'personas_en_casa': '¿Cuántas personas viven en casa?',
            'cuartos': '¿Cuántos cuartos tiene la casa?',
            'ac_count': '¿Tiene aire acondicionado?',
            'ac_horas_dia': 'Horas promedio de uso del A/C por día',
            'refrigeradores': '¿Cuántos refrigeradores tiene?',
            'ref_antiguedad': 'Antigüedad del refrigerador principal',
            'agua_caliente': '¿Cómo calienta el agua?',
            'lavadora': '¿Tiene lavadora?',
            'secadora': '¿Tiene secadora eléctrica?',
            'home_office': '¿Trabaja desde casa?',
            'bombeo_agua': '¿Tiene bomba de agua?',
        }
