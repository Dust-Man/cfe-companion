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
    list_display = ['id', 'bill', 'personas_en_casa', 'ac_count', 'refrigeradores', 'agua_caliente']
    list_filter = ['ac_count', 'refrigeradores', 'agua_caliente']


@admin.register(AnalysisResult)
class AnalysisResultAdmin(admin.ModelAdmin):
    list_display = ['id', 'bill', 'costo_estimado_mxn', 'co2e_kg', 'confianza_global', 'created_at']
    list_filter = ['confianza_global', 'created_at']
