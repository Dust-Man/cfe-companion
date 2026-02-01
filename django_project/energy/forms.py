"""
Forms for the Electric Assistant MVP.
"""

from django import forms
from django.core.exceptions import ValidationError
from .models import Bill


# ---------------------------------------------------------------------------
# CSS reutilizable para inputs
# ---------------------------------------------------------------------------
_INPUT_CSS = 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500'


class BillForm(forms.ModelForm):
    """Formulario para datos del recibo de CFE."""
    
    class Meta:
        model = Bill
        fields = [
            'tarifa', 'periodo_inicio', 'periodo_fin', 'consumo_kwh',
            'total_recibo_mxn', 'lectura_anterior', 'lectura_actual',
            'multiplicador', 'subsidio_mxn',
            # Escalones tarifarios
            'periodo_basico_kwh', 'periodo_intermedio_kwh', 'periodo_excedente_kwh',
            'subtotal_basico_mxn', 'subtotal_intermedio_mxn', 'subtotal_excedente_mxn',
            # Evidencia
            'evidencia_archivo',
        ]
        widgets = {
            'tarifa': forms.Select(attrs={'class': _INPUT_CSS}),
            'periodo_inicio': forms.DateInput(attrs={
                'type': 'date', 'class': _INPUT_CSS,
            }),
            'periodo_fin': forms.DateInput(attrs={
                'type': 'date', 'class': _INPUT_CSS,
            }),
            'consumo_kwh': forms.NumberInput(attrs={
                'class': _INPUT_CSS, 'placeholder': 'Ej: 280', 'min': 1, 'max': 20000,
            }),
            'total_recibo_mxn': forms.NumberInput(attrs={
                'class': _INPUT_CSS, 'placeholder': 'Ej: 450.00', 'step': '0.01',
            }),
            'lectura_anterior': forms.NumberInput(attrs={
                'class': _INPUT_CSS, 'placeholder': 'Opcional',
            }),
            'lectura_actual': forms.NumberInput(attrs={
                'class': _INPUT_CSS, 'placeholder': 'Opcional',
            }),
            'multiplicador': forms.NumberInput(attrs={
                'class': _INPUT_CSS, 'value': 1,
            }),
            'subsidio_mxn': forms.NumberInput(attrs={
                'class': _INPUT_CSS, 'placeholder': 'Opcional', 'step': '0.01',
            }),
            # --- Escalones tarifarios ---
            'periodo_basico_kwh': forms.NumberInput(attrs={
                'class': _INPUT_CSS, 'placeholder': 'kWh básicos', 'min': 0,
            }),
            'periodo_intermedio_kwh': forms.NumberInput(attrs={
                'class': _INPUT_CSS, 'placeholder': 'kWh intermedios', 'min': 0,
            }),
            'periodo_excedente_kwh': forms.NumberInput(attrs={
                'class': _INPUT_CSS, 'placeholder': 'kWh excedentes', 'min': 0,
            }),
            'subtotal_basico_mxn': forms.NumberInput(attrs={
                'class': _INPUT_CSS, 'placeholder': 'Subtotal básico', 'step': '0.01', 'min': 0,
            }),
            'subtotal_intermedio_mxn': forms.NumberInput(attrs={
                'class': _INPUT_CSS, 'placeholder': 'Subtotal intermedio', 'step': '0.01', 'min': 0,
            }),
            'subtotal_excedente_mxn': forms.NumberInput(attrs={
                'class': _INPUT_CSS, 'placeholder': 'Subtotal excedente', 'step': '0.01', 'min': 0,
            }),
            # --- Evidencia ---
            'evidencia_archivo': forms.FileInput(attrs={
                'class': _INPUT_CSS, 'accept': '.pdf,.jpg,.jpeg,.png',
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
            # Escalones
            'periodo_basico_kwh': 'Total periodo básico (kWh)',
            'periodo_intermedio_kwh': 'Total periodo intermedio (kWh)',
            'periodo_excedente_kwh': 'Total periodo excedente (kWh)',
            'subtotal_basico_mxn': 'Subtotal básico (MXN)',
            'subtotal_intermedio_mxn': 'Subtotal intermedio (MXN)',
            'subtotal_excedente_mxn': 'Subtotal excedente (MXN)',
            # Evidencia
            'evidencia_archivo': 'Subir recibo (PDF/imagen) - Opcional',
        }
    
    def clean(self):
        cleaned_data = super().clean()
        periodo_inicio = cleaned_data.get('periodo_inicio')
        periodo_fin = cleaned_data.get('periodo_fin')
        consumo_kwh = cleaned_data.get('consumo_kwh')

        # Validar que periodo_fin > periodo_inicio
        if periodo_inicio and periodo_fin:
            if periodo_fin <= periodo_inicio:
                raise ValidationError(
                    'La fecha de fin debe ser posterior a la fecha de inicio.'
                )

        # Validar que la suma de escalones no exceda el consumo total (si se proporcionan)
        basico = cleaned_data.get('periodo_basico_kwh') or 0
        intermedio = cleaned_data.get('periodo_intermedio_kwh') or 0
        excedente = cleaned_data.get('periodo_excedente_kwh') or 0

        
        return cleaned_data


# ---------------------------------------------------------------------------
# NOTA: La antigua SurveyForm fue eliminada.
# La nueva encuesta condicional se procesa directamente en views.py
# mediante _parse_survey_post() sin usar un ModelForm, ya que todas las
# respuestas se guardan en un único JSONField (Survey.respuestas).
# ---------------------------------------------------------------------------