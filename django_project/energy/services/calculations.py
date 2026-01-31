"""
Cálculos de consumo eléctrico para México (CFE).

NOTA IMPORTANTE: Estos cálculos son ESTIMACIONES basadas en reglas heurísticas.
No sustituyen una medición real del consumo. Las tarifas son aproximadas (2024).
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Any


# Factor de emisión CO2e para México (kgCO2e por kWh)
# Fuente: Factor de Emisión del Sistema Eléctrico Nacional 2023
CO2E_FACTOR = Decimal('0.444')


def compute_cost_mxn(consumo_kwh: int, tarifa: str) -> Decimal:
    """
    Calcula el costo estimado de la electricidad en MXN.
    
    Modelo simplificado para MVP:
    - DAC o consumo > 500 kWh: tarifa alta ($6.38/kWh)
    - Demás: escalonado (básico + intermedio + excedente)
    
    Args:
        consumo_kwh: Consumo en kWh del periodo
        tarifa: Código de tarifa CFE
    
    Returns:
        Costo estimado en MXN (con IVA 16%)
    """
    consumo = Decimal(consumo_kwh)
    
    # Tarifa DAC o alto consumo
    if tarifa == 'DAC' or consumo_kwh > 500:
        costo_base = consumo * Decimal('6.38')
    else:
        # Tarifa escalonada simplificada
        # Básico: primeros 150 kWh
        basico = min(consumo, Decimal('150')) * Decimal('0.98')
        
        # Intermedio: siguientes 130 kWh (151-280)
        intermedio = min(max(consumo - 150, 0), Decimal('130')) * Decimal('1.19')
        
        # Excedente: resto hasta 500 kWh
        excedente = max(consumo - 280, 0) * Decimal('3.52')
        
        costo_base = basico + intermedio + excedente
    
    # Aplicar IVA 16%
    costo_con_iva = costo_base * Decimal('1.16')
    
    return costo_con_iva.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def compute_co2e_kg(consumo_kwh: int) -> Decimal:
    """
    Calcula las emisiones de CO2 equivalente.
    
    Args:
        consumo_kwh: Consumo en kWh del periodo
    
    Returns:
        Emisiones en kg de CO2e
    """
    return (Decimal(consumo_kwh) * CO2E_FACTOR).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )


def compute_breakdown_and_recs(bill, survey) -> Dict[str, Any]:
    """
    Calcula el desglose de consumo por categorías y genera recomendaciones.
    
    Args:
        bill: Objeto Bill con datos del recibo
        survey: Objeto Survey con datos del cuestionario
    
    Returns:
        Dict con breakdown, recomendaciones, supuestos y confianza global
    """
    consumo_total = bill.consumo_kwh
    breakdown = {}
    supuestos = []
    
    # === CATEGORÍAS BASE ===
    
    # 1. Refrigeración (siempre presente)
    ref_base = 100 if survey.refrigeradores == 1 else 160
    if survey.ref_antiguedad == 'old':
        ref_kwh = int(ref_base * 1.20)  # +20% si es viejo
        supuestos.append("Refrigerador antiguo: +20% consumo estimado")
    elif survey.ref_antiguedad == 'new':
        ref_kwh = int(ref_base * 0.85)  # -15% si es nuevo
        supuestos.append("Refrigerador nuevo: -15% consumo estimado")
    else:
        ref_kwh = ref_base
    
    breakdown['Refrigeración'] = {
        'kwh': ref_kwh,
        'confianza': 'high'
    }
    
    # 2. Standby y misceláneos (mínimo 30 kWh, máximo 10% del total)
    standby_kwh = max(30, int(consumo_total * 0.10))
    breakdown['Standby / Misceláneos'] = {
        'kwh': standby_kwh,
        'confianza': 'low'
    }
    supuestos.append("Standby estimado como 10% del consumo total (mín. 30 kWh)")
    
    # === CATEGORÍAS VARIABLES ===
    
    # 3. Climatización (A/C)
    ac_kwh = 0
    if survey.ac_count > 0 and survey.ac_horas_dia > 0:
        # Estimación: unidades × horas × 1.2 kW × 60 días (bimestral)
        ac_kwh = int(survey.ac_count * survey.ac_horas_dia * 1.2 * 60)
        # Cap al 60% del consumo total
        ac_kwh = min(ac_kwh, int(consumo_total * 0.60))
        breakdown['Climatización (A/C)'] = {
            'kwh': ac_kwh,
            'confianza': 'medium'
        }
        supuestos.append(f"A/C: {survey.ac_count} unidad(es) × {survey.ac_horas_dia}h/día × 1.2kW × 60 días")
    
    # 4. Agua caliente eléctrica
    agua_kwh = 0
    if survey.agua_caliente == 'elec':
        # 60-120 kWh según personas
        agua_kwh = min(120, 40 + (survey.personas_en_casa * 15))
        breakdown['Agua caliente'] = {
            'kwh': agua_kwh,
            'confianza': 'medium'
        }
        supuestos.append(f"Calentador eléctrico para {survey.personas_en_casa} personas")
    
    # 5. Lavado
    lavado_kwh = 0
    if survey.lavadora:
        lavado_kwh += 20
        supuestos.append("Lavadora: ~20 kWh/bimestre estimado")
    if survey.secadora:
        lavado_kwh += 120
        supuestos.append("Secadora eléctrica: ~120 kWh/bimestre estimado")
    if lavado_kwh > 0:
        breakdown['Lavado'] = {
            'kwh': lavado_kwh,
            'confianza': 'medium' if survey.secadora else 'high'
        }
    
    # 6. Electrónicos / Home Office
    electronics_kwh = 0
    if survey.home_office:
        # 60-120 kWh para home office
        electronics_kwh = 80
        breakdown['Electrónicos / Home Office'] = {
            'kwh': electronics_kwh,
            'confianza': 'low'
        }
        supuestos.append("Home office: ~80 kWh/bimestre (PC + periféricos)")
    
    # 7. Bombeo de agua
    bombeo_kwh = 0
    if survey.bombeo_agua:
        bombeo_kwh = 50
        breakdown['Bombeo de agua'] = {
            'kwh': bombeo_kwh,
            'confianza': 'low'
        }
        supuestos.append("Bomba de agua: ~50 kWh/bimestre estimado")
    
    # === AJUSTE PARA CUADRAR AL TOTAL ===
    suma_parcial = sum(cat['kwh'] for cat in breakdown.values())
    
    if suma_parcial > consumo_total:
        # Reducir categorías flexibles proporcionalmente
        flexible_cats = ['Climatización (A/C)', 'Electrónicos / Home Office', 
                         'Standby / Misceláneos', 'Bombeo de agua']
        exceso = suma_parcial - consumo_total
        
        for cat in flexible_cats:
            if cat in breakdown and exceso > 0:
                reduccion = min(breakdown[cat]['kwh'] * 0.3, exceso)
                breakdown[cat]['kwh'] = max(10, int(breakdown[cat]['kwh'] - reduccion))
                exceso -= reduccion
        
        suma_parcial = sum(cat['kwh'] for cat in breakdown.values())
    
    # Asignar residual a "Otros"
    residual = consumo_total - suma_parcial
    if residual > 5:
        breakdown['Otros'] = {
            'kwh': residual,
            'confianza': 'low'
        }
        supuestos.append(f"Otros consumos no identificados: {residual} kWh")
    elif residual < 0:
        # Ajustar standby si hay exceso
        if 'Standby / Misceláneos' in breakdown:
            breakdown['Standby / Misceláneos']['kwh'] = max(
                10, breakdown['Standby / Misceláneos']['kwh'] + residual
            )
    
    # Calcular porcentajes
    for cat in breakdown:
        breakdown[cat]['pct'] = round(breakdown[cat]['kwh'] / consumo_total * 100, 1)
    
    # === RECOMENDACIONES ===
    costo_por_kwh = compute_cost_mxn(consumo_total, bill.tarifa) / Decimal(consumo_total)
    recomendaciones = []
    
    # Ordenar categorías por consumo
    cats_ordenadas = sorted(breakdown.items(), key=lambda x: x[1]['kwh'], reverse=True)
    
    # Recomendación de A/C
    if 'Climatización (A/C)' in breakdown and breakdown['Climatización (A/C)']['kwh'] > 100:
        ahorro_kwh = int(breakdown['Climatización (A/C)']['kwh'] * 0.12)
        recomendaciones.append({
            'titulo': 'Optimizar uso del aire acondicionado',
            'descripcion': 'Subir el termostato 2°C, limpiar filtros mensualmente, y sellar puertas/ventanas.',
            'ahorro_kwh': ahorro_kwh,
            'ahorro_mxn': float((Decimal(ahorro_kwh) * costo_por_kwh).quantize(Decimal('0.01'))),
            'ahorro_co2e': float(compute_co2e_kg(ahorro_kwh)),
            'costo': 'gratis',
            'dificultad': 'fácil'
        })
    
    # Recomendación de refrigerador viejo
    if survey.ref_antiguedad == 'old':
        ahorro_kwh = int(ref_kwh * 0.10)
        recomendaciones.append({
            'titulo': 'Revisar refrigerador antiguo',
            'descripcion': 'Verificar sello de la puerta, ajustar temperatura a 4°C. A mediano plazo, considerar reemplazo.',
            'ahorro_kwh': ahorro_kwh,
            'ahorro_mxn': float((Decimal(ahorro_kwh) * costo_por_kwh).quantize(Decimal('0.01'))),
            'ahorro_co2e': float(compute_co2e_kg(ahorro_kwh)),
            'costo': 'bajo',
            'dificultad': 'fácil'
        })
    
    # Recomendación de iluminación (siempre)
    ahorro_led = 20
    recomendaciones.append({
        'titulo': 'Cambiar a iluminación LED',
        'descripcion': 'Reemplazar focos incandescentes por LED y apagar luces al salir.',
        'ahorro_kwh': ahorro_led,
        'ahorro_mxn': float((Decimal(ahorro_led) * costo_por_kwh).quantize(Decimal('0.01'))),
        'ahorro_co2e': float(compute_co2e_kg(ahorro_led)),
        'costo': 'bajo',
        'dificultad': 'fácil'
    })
    
    # Recomendación de standby
    if 'Standby / Misceláneos' in breakdown and breakdown['Standby / Misceláneos']['kwh'] > 40:
        ahorro_standby = 15
        recomendaciones.append({
            'titulo': 'Reducir consumo standby',
            'descripcion': 'Usar regletas con switch para apagar dispositivos completamente cuando no se usen.',
            'ahorro_kwh': ahorro_standby,
            'ahorro_mxn': float((Decimal(ahorro_standby) * costo_por_kwh).quantize(Decimal('0.01'))),
            'ahorro_co2e': float(compute_co2e_kg(ahorro_standby)),
            'costo': 'bajo',
            'dificultad': 'fácil'
        })
    
    # Recomendación de secadora
    if survey.secadora:
        ahorro_sec = 60
        recomendaciones.append({
            'titulo': 'Reducir uso de secadora',
            'descripcion': 'Secar ropa al aire libre cuando sea posible. Usar la secadora solo en emergencias.',
            'ahorro_kwh': ahorro_sec,
            'ahorro_mxn': float((Decimal(ahorro_sec) * costo_por_kwh).quantize(Decimal('0.01'))),
            'ahorro_co2e': float(compute_co2e_kg(ahorro_sec)),
            'costo': 'gratis',
            'dificultad': 'fácil'
        })
    
    # Ordenar por ahorro y tomar top 3
    recomendaciones = sorted(recomendaciones, key=lambda x: x['ahorro_kwh'], reverse=True)[:3]
    
    # === CONFIANZA GLOBAL ===
    # Alta: si tiene lecturas y total MXN declarado
    # Media: solo datos básicos
    # Baja: tarifa desconocida o datos incompletos
    
    if bill.tarifa == 'DESCONOZCO':
        confianza_global = 'low'
        supuestos.append("Tarifa desconocida: se usó tarifa promedio")
    elif bill.total_recibo_mxn and bill.lectura_anterior and bill.lectura_actual:
        confianza_global = 'high'
    else:
        confianza_global = 'medium'
    
    return {
        'breakdown': breakdown,
        'recomendaciones': recomendaciones,
        'supuestos': supuestos,
        'confianza_global': confianza_global
    }
