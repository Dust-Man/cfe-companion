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
    
    # Campos requeridos
    tarifa = models.CharField(max_length=20, choices=TARIFA_CHOICES)
    periodo_inicio = models.DateField()
    periodo_fin = models.DateField()
    consumo_kwh = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5000)]
    )
    
    # Campos opcionales para validación
    total_recibo_mxn = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    lectura_anterior = models.PositiveIntegerField(null=True, blank=True)
    lectura_actual = models.PositiveIntegerField(null=True, blank=True)
    multiplicador = models.PositiveIntegerField(default=1)
    subsidio_mxn = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    
    # Escalones tarifarios (extraídos por OCR o ingresados manualmente)
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
    
    # Evidencia opcional
    evidencia_archivo = models.FileField(
        upload_to='evidencias/', null=True, blank=True
    )
    
    # Flag para demos
    is_demo = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Recibo {self.tarifa} - {self.consumo_kwh} kWh ({self.periodo_inicio} a {self.periodo_fin})"
    
    def dias_periodo(self):
        """Retorna días del periodo de facturación."""
        return (self.periodo_fin - self.periodo_inicio).days

    @property
    def consumo_basico(self):
        """Consumo en rango básico."""
        return self.periodo_basico_kwh or 0

    @property
    def consumo_intermedio(self):
        """Consumo en rango intermedio."""
        return self.periodo_intermedio_kwh or 0

    @property
    def consumo_excedente(self):
        """Consumo en rango excedente."""
        return self.periodo_excedente_kwh or 0

    @property
    def precio_unitario(self):
        """Precio unitario promedio."""
        if self.consumo_kwh and self.total_recibo_mxn:
            return (self.total_recibo_mxn / self.consumo_kwh).quantize(Decimal('0.01'))
        return Decimal('0.00')

    @property
    def subsidio(self):
        """Subsidio aplicado."""
        return self.subsidio_mxn or Decimal('0.00')

    @property
    def demanda_max(self):
        """Demanda máxima (estimada como consumo diario promedio)."""
        if self.dias_periodo() > 0:
            return Decimal(self.consumo_kwh / self.dias_periodo()).quantize(Decimal('0.1'))
        return Decimal('0.0')

    @property
    def subtotal_energia(self):
        """Subtotal de energía."""
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
        """IVA calculado (16% del subtotal de energía)."""
        return (self.subtotal_energia * Decimal('0.16')).quantize(Decimal('0.01'))

    @property
    def dap(self):
        """DAP (Alumbrado público) - estimado como 5% del subtotal."""
        return (self.subtotal_energia * Decimal('0.05')).quantize(Decimal('0.01'))


class Survey(models.Model):
    """Cuestionario sobre el hogar y aparatos."""
    
    AC_COUNT_CHOICES = [
        (0, 'No tengo'),
        (1, '1 unidad'),
        (2, '2 o más'),
    ]
    
    REF_COUNT_CHOICES = [
        (1, '1 refrigerador'),
        (2, '2 o más'),
    ]
    
    REF_ANTIGUEDAD_CHOICES = [
        ('new', 'Nuevo (menos de 5 años)'),
        ('mid', 'Medio (5-12 años)'),
        ('old', 'Antiguo (más de 12 años)'),
    ]
    
    AGUA_CALIENTE_CHOICES = [
        ('gas', 'Gas (boiler/calentador)'),
        ('elec', 'Eléctrico'),
        ('none', 'No uso agua caliente'),
    ]
    
    bill = models.OneToOneField(Bill, on_delete=models.CASCADE, related_name='survey')
    
    # Hogar básico
    personas_en_casa = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(15)],
        verbose_name="Personas en casa"
    )
    cuartos = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(20)],
        verbose_name="Número de cuartos"
    )
    
    # Aire acondicionado
    ac_count = models.IntegerField(
        choices=AC_COUNT_CHOICES, default=0,
        verbose_name="Unidades de A/C"
    )
    ac_horas_dia = models.PositiveIntegerField(
        default=0,
        validators=[MaxValueValidator(24)],
        verbose_name="Horas de uso A/C por día"
    )
    
    # Refrigeración
    refrigeradores = models.IntegerField(
        choices=REF_COUNT_CHOICES, default=1,
        verbose_name="Refrigeradores"
    )
    ref_antiguedad = models.CharField(
        max_length=10, choices=REF_ANTIGUEDAD_CHOICES, default='mid',
        verbose_name="Antigüedad del refrigerador principal"
    )
    
    # Agua caliente
    agua_caliente = models.CharField(
        max_length=10, choices=AGUA_CALIENTE_CHOICES, default='gas',
        verbose_name="Tipo de calentador de agua"
    )
    
    # Lavado
    lavadora = models.BooleanField(default=True, verbose_name="¿Tiene lavadora?")
    secadora = models.BooleanField(default=False, verbose_name="¿Tiene secadora eléctrica?")
    
    # Otros
    home_office = models.BooleanField(
        default=False, verbose_name="¿Trabaja desde casa (home office)?"
    )
    bombeo_agua = models.BooleanField(
        default=False, verbose_name="¿Tiene bomba de agua (tinaco/cisterna)?"
    )
    
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
    
    # Resultados principales
    costo_estimado_mxn = models.DecimalField(max_digits=10, decimal_places=2)
    co2e_kg = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Desglose por categorías (JSON)
    # Formato: {"categoria": {"kwh": X, "pct": Y, "confianza": "high|medium|low"}}
    breakdown_json = models.JSONField(default=dict)
    
    # Recomendaciones (JSON)
    # Formato: [{"titulo": "", "descripcion": "", "ahorro_kwh": X, "ahorro_mxn": X, 
    #            "ahorro_co2e": X, "costo": "gratis|bajo|medio", "dificultad": "fácil|media"}]
    recomendaciones_json = models.JSONField(default=list)
    
    # Supuestos del cálculo (JSON)
    supuestos_json = models.JSONField(default=list)
    
    # Confianza global
    confianza_global = models.CharField(
        max_length=10, choices=CONFIDENCE_CHOICES, default='medium'
    )
    
    def __str__(self):
        return f"Análisis: {self.costo_estimado_mxn} MXN, {self.co2e_kg} kg CO2e"