"""
Models for the Electric Assistant MVP.
"""

from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Bill(models.Model):
    """Modelo para el recibo de CFE."""
    
    TARIFA_CHOICES = [
        ('1', '1 - Básica'),
        ('1A', '1A - Cálido extremo'),
        ('1B', '1B - Cálido'),
        ('1C', '1C - Cálido templado'),
        ('1D', '1D - Cálido húmedo'),
        ('1E', '1E - Cálido muy cálido'),
        ('1F', '1F - Cálido extremo prolongado'),
        ('DAC', 'DAC - Doméstica Alto Consumo'),
        ('DESCONOZCO', 'No sé mi tarifa'),
    ]
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    tarifa = models.CharField(max_length=20, choices=TARIFA_CHOICES)
    periodo_inicio = models.DateField()
    periodo_fin = models.DateField()
    consumo_kwh = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    
    total_recibo_mxn = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    lectura_anterior = models.PositiveIntegerField(null=True, blank=True)
    lectura_actual = models.PositiveIntegerField(null=True, blank=True)
    multiplicador = models.PositiveIntegerField(default=1)
    subsidio_mxn = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    
    periodo_basico_kwh = models.PositiveIntegerField(null=True, blank=True)
    periodo_intermedio_kwh = models.PositiveIntegerField(null=True, blank=True)
    periodo_excedente_kwh = models.PositiveIntegerField(null=True, blank=True)
    subtotal_basico_mxn = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    subtotal_intermedio_mxn = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    subtotal_excedente_mxn = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    
    evidencia_archivo = models.FileField(
        upload_to='evidencias/', null=True, blank=True
    )
    
    is_demo = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Recibo {self.tarifa} - {self.consumo_kwh} kWh ({self.periodo_inicio} a {self.periodo_fin})"
    
    def dias_periodo(self):
        return (self.periodo_fin - self.periodo_inicio).days

    @property
    def consumo_basico(self):
        return self.periodo_basico_kwh or 0

    @property
    def consumo_intermedio(self):
        return self.periodo_intermedio_kwh or 0

    @property
    def consumo_excedente(self):
        return self.periodo_excedente_kwh or 0

    @property
    def precio_unitario(self):
        if self.consumo_kwh and self.total_recibo_mxn:
            return (self.total_recibo_mxn / self.consumo_kwh).quantize(Decimal('0.01'))
        return Decimal('0.00')

    @property
    def subsidio(self):
        return self.subsidio_mxn or Decimal('0.00')

    @property
    def demanda_max(self):
        if self.dias_periodo() > 0:
            return Decimal(self.consumo_kwh / self.dias_periodo()).quantize(Decimal('0.1'))
        return Decimal('0.0')

    @property
    def subtotal_energia(self):
        subtotal = Decimal('0.00')
        if self.subtotal_basico_mxn:
            subtotal += self.subtotal_basico_mxn
        if self.subtotal_intermedio_mxn:
            subtotal += self.subtotal_intermedio_mxn
        if self.subtotal_excedente_mxn:
            subtotal += self.subtotal_excedente_mxn
        return subtotal

    @property
    def iva(self):
        return (self.subtotal_energia * Decimal('0.16')).quantize(Decimal('0.01'))

    @property
    def precio_basico(self):
        if self.consumo_basico and self.subtotal_basico_mxn:
            return (self.subtotal_basico_mxn / self.consumo_basico).quantize(Decimal('0.01'))
        return Decimal('0.00')

    @property
    def precio_intermedio(self):
        if self.consumo_intermedio and self.subtotal_intermedio_mxn:
            return (self.subtotal_intermedio_mxn / self.consumo_intermedio).quantize(Decimal('0.01'))
        return Decimal('0.00')

    @property
    def precio_excedente(self):
        if self.consumo_excedente and self.subtotal_excedente_mxn:
            return (self.subtotal_excedente_mxn / self.consumo_excedente).quantize(Decimal('0.01'))
        return Decimal('0.00')


class Survey(models.Model):
    """
    Cuestionario sobre el hogar — versión nueva (condicional).
    
    Las respuestas se guardan como un único JSON en `respuestas`.
    Esto permite que la encuesta condicional agregue o omita campos
    sin necesitar columnas extras ni migraciones nuevas.
    
    Estructura esperada de `respuestas`:
    {
        # Pantalla 1 — cambios recientes (lista de strings)
        "cambios_recientes": ["ola_calor", "mas_gente", ...],

        # Pantalla 2 — A/C
        "tiene_ac": "no" | "minisplit_inverter" | "minisplit_no_inverter" | "ventana" | "no_se",
        "ac_unidades": "1" | "2" | "3+",          # solo si tiene_ac != "no"
        "ac_dias_semana": "1-2" | "3-4" | "5-6" | "7",
        "ac_horas_dia": "1-2" | "3-5" | "6-8" | "9+",
        "ac_temperatura": "18-20" | "21-23" | "24-26" | "no_se",

        # Pantalla 3 — agua caliente
        "agua_caliente_tipo": "gas" | "electrico" | "mixto",
        "agua_caliente_equipo": ["boiler_electrico", "regadera_electrica", ...],
        "agua_personas": "1" | "2" | "3-4" | "5+",
        "agua_duracion": "3-5" | "6-10" | "11-15" | "16+",

        # Pantalla 4 — refrigeración
        "refrigeradores": "0" | "1" | "2" | "3+",
        "ref_antiguedad": "nuevo" | "medio" | "viejo" | "no_se",

        # Pantalla 5 — secadora
        "tiene_secadora": "no" | "electrica" | "gas" | "no_se",
        "secadora_cargas": "1-2" | "3-4" | "5-7" | "8+",
        "secadora_alto_calor": "si" | "no" | "no_se",

        # Pantalla 6 — bombas
        "tiene_bomba": "no" | "si" | "no_se",
        "bomba_frecuencia": "poco" | "normal" | "mucho" | "no_se",
        "tiene_bomba_alberca": "no" | "si",
        "bomba_alberca_horas": "1-2" | "3-5" | "6+",

        # Pantalla 7 — calefactor eléctrico
        "calefactor": "no" | "ocasional" | "frecuente" | "no_se",
        "calefactor_horas": "1-2" | "3-5" | "6-8" | "9+",

        # Pantalla 8 — cocina
        "cocina_tipo": "gas" | "electrica" | "mixta",
        "cocina_horno": "no" | "1-2" | "3+",
        "cocina_airfryer": "no" | "1-3" | "4+",
        "cocina_parrilla": "no" | "poco" | "diario",
        "cocina_hervidor": "no" | "1-3" | "diario",

        # Pantalla 9 — siempre encendidos
        "tvs": "0" | "1" | "2" | "3+",
        "pc_uso": "no" | "1-3" | "4-8" | "9+",
        "consola": "no" | "1-3" | "4+",
        "siempre_encendidos": ["router", "camaras", "servidor"],

        # Pantalla 10 — culpables ocultos
        "culpables_ocultos": ["lavavajillas", "deshumidificador", ...],
        "culpables_uso": "solo_a_veces" | "1-2" | "3-5" | "6+" | "no_se",
    }
    """
    bill = models.OneToOneField(Bill, on_delete=models.CASCADE, related_name='survey')
    respuestas = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Encuesta para {self.bill}"


class AnalysisResult(models.Model):
    """Resultados del análisis de consumo."""
    
    CONFIDENCE_CHOICES = [
        ('high', 'Alta'),
        ('medium', 'Media'),
        ('low', 'Baja'),
    ]
    
    bill = models.OneToOneField(Bill, on_delete=models.CASCADE, related_name='analysis')
    created_at = models.DateTimeField(auto_now_add=True)
    
    costo_estimado_mxn = models.DecimalField(max_digits=10, decimal_places=2)
    co2e_kg = models.DecimalField(max_digits=10, decimal_places=2)
    
    breakdown_json = models.JSONField(default=dict)
    recomendaciones_json = models.JSONField(default=list)
    supuestos_json = models.JSONField(default=list)
    
    confianza_global = models.CharField(
        max_length=10, choices=CONFIDENCE_CHOICES, default='medium'
    )
    
    def __str__(self):
        return f"Análisis: {self.costo_estimado_mxn} MXN, {self.co2e_kg} kg CO2e"