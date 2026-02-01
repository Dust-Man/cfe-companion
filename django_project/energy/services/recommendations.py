"""
Servicio de recomendaciones powered by OpenAI.

Entrada:
    - respuestas: dict con las respuestas de la nueva encuesta
    - tarifa: string (ej "1C", "DAC")
    - consumo_kwh: int

Salida:
    lista de 5 dicts con la estructura:
    {
        "titulo": str,
        "descripcion": str,
        "tipo": "sin_inversion" | "con_inversion",
        "ahorro_mensual_mxn": float,       # estimado por OpenAI
        "ahorro_anual_mxn": float,
        "reduccion_co2_kg_anual": float,
        "costo_inversion_mxn": float | None,  # solo si tipo == "con_inversion"
        "retorno_meses": int | None,          # solo si tipo == "con_inversion"
        "prioridad": int                      # 1 = más importante
    }
"""

import json
import os
import re
from typing import Optional

from openai import OpenAI


# ─── Tarifas por kWh (MXN) ──────────────────────────────────────────────────
TARIFAS = {
    "1":   1.30,
    "1A":  1.147,
    "1B":  1.147,
    "1C":  1.47,
    "1D":  1.47,
    "1E":  1.332,
    "1F":  2.494,
    "DAC": 3.12,
}

# Factor CO2e México 2023 (kgCO2e / kWh)
CO2E_FACTOR = 0.444


def _precio_kwh(tarifa: str) -> float:
    """Retorna precio $/kWh según tarifa. Si no se conoce, usa promedio."""
    return TARIFAS.get(tarifa.upper().replace("TARIFA ", ""), 1.47)


def _build_prompt(respuestas: dict, tarifa: str, consumo_kwh: int) -> str:
    """
    Construye el prompt que le mandamos a OpenAI.
    Incluye todas las respuestas de forma legible y las instrucciones
    estrictas de formato de salida.
    """
    precio = _precio_kwh(tarifa)

    # ─── Resumen legible de respuestas ──────────────────────────────────
    lines = []

    # 1. Cambios recientes
    cambios = respuestas.get("cambios_recientes", [])
    lines.append(f"Cambios recientes en el hogar: {', '.join(cambios) if cambios else 'Ninguno reportado'}")

    # 2. A/C
    ac = respuestas.get("tiene_ac", "no")
    lines.append(f"Aire acondicionado: {ac}")
    if ac not in ("no",):
        lines.append(f"  Unidades de A/C: {respuestas.get('ac_unidades', '?')}")
        lines.append(f"  Días/semana en uso: {respuestas.get('ac_dias_semana', '?')}")
        lines.append(f"  Horas/día promedio: {respuestas.get('ac_horas_dia', '?')}")
        lines.append(f"  Temperatura configurada: {respuestas.get('ac_temperatura', '?')}°C")

    # 3. Agua caliente
    agua_tipo = respuestas.get("agua_caliente_tipo", "gas")
    lines.append(f"Calentamiento de agua: {agua_tipo}")
    if agua_tipo in ("electrico", "mixto"):
        lines.append(f"  Equipo: {respuestas.get('agua_caliente_equipo', [])}")
        lines.append(f"  Personas que se bañan/día: {respuestas.get('agua_personas', '?')}")
        lines.append(f"  Duración promedio baño: {respuestas.get('agua_duracion', '?')} min")

    # 4. Refrigeración
    lines.append(f"Refrigeradores: {respuestas.get('refrigeradores', '1')}")
    lines.append(f"Antigüedad del principal: {respuestas.get('ref_antiguedad', 'no_se')}")

    # 5. Secadora
    secadora = respuestas.get("tiene_secadora", "no")
    lines.append(f"Secadora: {secadora}")
    if secadora == "electrica":
        lines.append(f"  Cargas/semana: {respuestas.get('secadora_cargas', '?')}")
        lines.append(f"  Usa alto calor: {respuestas.get('secadora_alto_calor', '?')}")

    # 6. Bombas
    bomba = respuestas.get("tiene_bomba", "no")
    lines.append(f"Bomba de agua: {bomba}")
    if bomba == "si":
        lines.append(f"  Frecuencia: {respuestas.get('bomba_frecuencia', '?')}")
    bomba_alberca = respuestas.get("tiene_bomba_alberca", "no")
    lines.append(f"Bomba de alberca: {bomba_alberca}")
    if bomba_alberca == "si":
        lines.append(f"  Horas/día: {respuestas.get('bomba_alberca_horas', '?')}")

    # 7. Calefactor
    calef = respuestas.get("calefactor", "no")
    lines.append(f"Calefactor eléctrico: {calef}")
    if calef in ("ocasional", "frecuente"):
        lines.append(f"  Horas/día en días de uso: {respuestas.get('calefactor_horas', '?')}")

    # 8. Cocina
    lines.append(f"Cocina: {respuestas.get('cocina_tipo', 'gas')}")
    lines.append(f"  Horno eléctrico: {respuestas.get('cocina_horno', 'no')}")
    lines.append(f"  Airfryer: {respuestas.get('cocina_airfryer', 'no')}")
    lines.append(f"  Parrilla eléctrica: {respuestas.get('cocina_parrilla', 'no')}")
    lines.append(f"  Hervidor eléctrico: {respuestas.get('cocina_hervidor', 'no')}")

    # 9. Siempre encendidos
    lines.append(f"TVs en uso diario: {respuestas.get('tvs', '0')}")
    lines.append(f"PC/laptop uso diario: {respuestas.get('pc_uso', 'no')}")
    lines.append(f"Consola de videojuegos: {respuestas.get('consola', 'no')}")
    lines.append(f"Dispositivos 24/7: {respuestas.get('siempre_encendidos', [])}")

    # 10. Culpables ocultos
    culpables = respuestas.get("culpables_ocultos", [])
    lines.append(f"Otros aparatos: {', '.join(culpables) if culpables else 'Ninguno'}")
    if culpables:
        lines.append(f"  Uso típico: {respuestas.get('culpables_uso', '?')}")

    resumen = "\n".join(lines)

    prompt = f"""Eres un experto en eficiencia energética doméstica en México.
Un usuario ha respondido una encuesta sobre su consumo eléctrico. Basándote ÚNICAMENTE en sus respuestas, genera exactamente 5 recomendaciones personalizadas para reducir su consumo y su impacto ambiental.

═══════════════════════════════════════
DATOS DEL USUARIO
═══════════════════════════════════════
Tarifa CFE: {tarifa}
Precio del kWh según su tarifa: ${precio:.3f} MXN/kWh
Consumo del periodo: {consumo_kwh} kWh
Factor de emisiones de CO₂e en México: {CO2E_FACTOR} kg CO₂e por kWh consumido

Respuestas de la encuesta:
{resumen}

═══════════════════════════════════════
INSTRUCCIONES ESTRICTAS
═══════════════════════════════════════
1. Genera EXACTAMENTE 5 recomendaciones.
2. De las 5:
   - 3 deben ser de tipo "sin_inversion" (cambios de hábito, ajustes gratuitos o de costo mínimo < $200 MXN).
   - 2 deben ser de tipo "con_inversion" (compra de aparato, mejora física, etc. con costo > $200 MXN).
3. Cada recomendación debe ser DIRECTAMENTE relevante a las respuestas del usuario.
   Si el usuario NO tiene A/C, NO generes recomendaciones sobre A/C.
   Si el usuario NO tiene secadora eléctrica, NO generes recomendaciones sobre secadora. Etc.
4. Para el beneficio económico, CALCULA:
   - ahorro_mensual_mxn: estimación de cuánto se ahorra por mes en MXN, usando el precio del kWh de su tarifa (${precio:.3f}/kWh).
   - ahorro_anual_mxn: ahorro_mensual_mxn × 12.
5. Para el impacto ambiental, CALCULA:
   - reduccion_co2_kg_anual: los kWh ahorrados por año × {CO2E_FACTOR} (factor de emisiones México).
6. Para las recomendaciones "con_inversion", incluye:
   - costo_inversion_mxn: costo estimado de la inversión en MXN.
   - retorno_meses: costo_inversion_mxn / ahorro_mensual_mxn (redondeado al entero más cercano).
7. Ordena por prioridad: la más impactante primero (prioridad: 1 = máxima).
8. Los cálculos deben ser REALISTASS y conservative. No exageres los ahorros.

═══════════════════════════════════════
FORMATO DE SALIDA
═══════════════════════════════════════
Devuelve ÚNICAMENTE un JSON válido (sin texto extra, sin markdown, sin ```). 
Estructura exacta:

[
  {{
    "titulo": "Título corto y descriptivo",
    "descripcion": "Descripción práctica de qué hacer exactamente (2-3 oraciones).",
    "tipo": "sin_inversion" o "con_inversion",
    "ahorro_mensual_mxn": <número float>,
    "ahorro_anual_mxn": <número float>,
    "reduccion_co2_kg_anual": <número float>,
    "costo_inversion_mxn": <número float o null>,
    "retorno_meses": <número int o null>,
    "prioridad": <1 al 5>
  }},
  ...
]
"""
    return prompt


def get_recommendations(respuestas: dict, tarifa: str, consumo_kwh: int) -> list:
    """
    Llama a OpenAI y retorna las 5 recomendaciones parseadas.
    En caso de error retorna una lista vacía.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY no configurada en variables de entorno.")

    client = OpenAI(api_key=api_key)
    prompt = _build_prompt(respuestas, tarifa, consumo_kwh)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.3,
        max_tokens=2000,
        messages=[
            {"role": "user", "content": prompt}
        ],
    )

    raw = response.choices[0].message.content.strip()

    # Quitar posibles ```json ... ``` que el modelo a veces agrega
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        recs = json.loads(raw)
    except json.JSONDecodeError:
        # Intento de recuperación: buscar el primer [ ... ] en el texto
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if match:
            recs = json.loads(match.group())
        else:
            return []

    # Validación básica: debe ser lista de 5 dicts
    if not isinstance(recs, list):
        return []

    # Asegurar campos requeridos y tipos
    cleaned = []
    for i, r in enumerate(recs[:5]):  # máximo 5
        cleaned.append({
            "titulo": str(r.get("titulo", "Sin título")),
            "descripcion": str(r.get("descripcion", "")),
            "tipo": r.get("tipo", "sin_inversion"),
            "ahorro_mensual_mxn": round(float(r.get("ahorro_mensual_mxn", 0)), 2),
            "ahorro_anual_mxn": round(float(r.get("ahorro_anual_mxn", 0)), 2),
            "reduccion_co2_kg_anual": round(float(r.get("reduccion_co2_kg_anual", 0)), 2),
            "costo_inversion_mxn": round(float(r["costo_inversion_mxn"]), 2) if r.get("costo_inversion_mxn") else None,
            "retorno_meses": int(r["retorno_meses"]) if r.get("retorno_meses") else None,
            "prioridad": int(r.get("prioridad", i + 1)),
        })

    return cleaned