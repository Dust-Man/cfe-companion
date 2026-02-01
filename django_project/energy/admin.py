"""
Admin configuration for Energy app.
"""

from django.contrib import admin
from .models import Bill, Survey, AnalysisResult


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ['id', 'tarifa', 'consumo_kwh', 'periodo_inicio', 'periodo_fin', 'is_demo', 'created_at']
    list_filter = ['tarifa', 'is_demo', 'created_at']
    search_fields = ['tarifa']
    ordering = ['-created_at']


@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    list_display = ['id', 'bill', 'created_at', 'resumen_respuestas']
    ordering = ['-created_at']

    def resumen_respuestas(self, obj):
        """Muestra un resumen rápido de las respuestas clave."""
        r = obj.respuestas
        partes = []
        # A/C
        ac = r.get('tiene_ac', 'no')
        partes.append(f"A/C: {ac}")
        # Refrigeradores
        partes.append(f"Refri: {r.get('refrigeradores', '?')}")
        # Agua caliente
        partes.append(f"Agua: {r.get('agua_caliente_tipo', '?')}")
        # Secadora
        partes.append(f"Secadora: {r.get('tiene_secadora', 'no')}")
        return " | ".join(partes)

    resumen_respuestas.short_description = "Resumen"


@admin.register(AnalysisResult)
class AnalysisResultAdmin(admin.ModelAdmin):
    list_display = ['id', 'bill', 'costo_estimado_mxn', 'co2e_kg', 'confianza_global', 'created_at']
    list_filter = ['confianza_global', 'created_at']