"""
Extracción de datos de recibos CFE mediante visión de OpenAI.

Mapeo OCR → modelo Bill:
    consumo_total      → consumo_kwh
    lectura_anterior   → lectura_anterior
    lectura_actual     → lectura_actual
    total_pagar        → total_recibo_mxn
    tarifa             → tarifa
    subsidio           → subsidio_mxn
    multiplicador      → multiplicador
    periodo_facturado  → periodo_inicio / periodo_fin  (se parsea en _parse_periodo)

Campos adicionales para el dashboard (escalones tarifarios):
    periodo_basico_kwh      → periodo_basico_kwh
    periodo_intermedio_kwh  → periodo_intermedio_kwh
    periodo_excedente_kwh   → periodo_excedente_kwh
    subtotal_basico_mxn     → subtotal_basico_mxn
    subtotal_intermedio_mxn → subtotal_intermedio_mxn
    subtotal_excedente_mxn  → subtotal_excedente_mxn
"""

import base64
import json
import re
from datetime import datetime
from typing import Optional

from openai import OpenAI


# Prompt que pide SOLO los campos que el modelo necesita.
_PROMPT = """
Extrae la información del recibo de luz CFE.

Devuelve ÚNICAMENTE JSON válido con esta estructura exacta:

{
  "consumo_total": number,
  "lectura_anterior": number,
  "lectura_actual": number,
  "total_pagar": number,
  "tarifa": string,
  "subsidio": number,
  "multiplicador": number,
  "periodo_facturado": string,
  "periodo_basico_kwh": number,
  "periodo_intermedio_kwh": number,
  "periodo_excedente_kwh": number,
  "subtotal_basico_mxn": number,
  "subtotal_intermedio_mxn": number,
  "subtotal_excedente_mxn": number
}

Notas:
- "consumo_total" es el consumo total en kWh del periodo facturado, esta inmediatamente abajo de Total periodo
- "tarifa" es el código que aparece como "TARIFA 1", "TARIFA 1C", "TARIFA DAC", etc.
  Devuelve solo el código: "1", "1A", "1B", "1C", "1D", "1E", "1F" o "DAC".
- "periodo_facturado" es el rango de fechas del periodo, ej: "01/12/2024 - 31/01/2025".
- "subsidio" es el monto de subsidio en MXN si aparece en el recibo.
- "multiplicador" es el factor del medidor (normalmente 1).
- "periodo_basico_kwh", "periodo_intermedio_kwh", "periodo_excedente_kwh" son los kWh
  consumidos en cada escalón tarifario. En el recibo aparecen en la tabla de cargos por
  energía, en la columna de cantidad o "Total periodo" junto a las etiquetas
  "Básico", "Intermedio" y "Excedente".
- "subtotal_basico_mxn", "subtotal_intermedio_mxn", "subtotal_excedente_mxn" son los
  importes en MXN de cada escalón (antes de IVA). Aparecen en la misma tabla, en la
  columna de importe o "Subtotal", junto a las etiquetas correspondientes.
- Si un campo no existe o no se puede leer, usa null.
- No agregues texto extra, solo el JSON.
"""


class CFEVisionExtractor:
    """Extrae datos de un recibo CFE usando GPT-4o-mini con visión."""

    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)

    # ------------------------------------------------------------------
    # Público
    # ------------------------------------------------------------------

    def extract(self, image_path: str) -> dict:
        """
        Recibe la ruta de una imagen y retorna un dict con los campos
        mapeados al modelo Bill.  Nunca lanza por parsing interno;
        campos que no se pudieron extraer quedan en None.
        """
        b64 = self._encode_image(image_path)
        raw = self._call_api(b64)
        return self._map_to_bill_fields(raw)

    def extract_from_bytes(self, image_bytes: bytes, mime: str = "image/png") -> dict:
        """Versión que acepta bytes directamente (útil desde Django UploadedFile)."""
        b64 = base64.b64encode(image_bytes).decode()
        raw = self._call_api(b64, mime)
        return self._map_to_bill_fields(raw)

    # ------------------------------------------------------------------
    # Interno — llamada a la API
    # ------------------------------------------------------------------

    def _encode_image(self, path: str) -> str:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()

    def _call_api(self, b64: str, mime: str = "image/png") -> dict:
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": _PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime};base64,{b64}"
                            },
                        },
                    ],
                }
            ],
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)

    # ------------------------------------------------------------------
    # Interno — mapeo al modelo Bill
    # ------------------------------------------------------------------

    def _map_to_bill_fields(self, raw: dict) -> dict:
        """
        Transforma la respuesta cruda de la API en un dict cuyas claves
        coinciden con los campos de BillForm + campos extra del dashboard.
        Incluye periodo_inicio y periodo_fin parseados desde periodo_facturado.
        """
        periodo_inicio, periodo_fin = _parse_periodo(raw.get("periodo_facturado"))

        tarifa_raw = raw.get("tarifa")
        tarifa = _normalize_tarifa(tarifa_raw) if tarifa_raw else None

        return {
            # --- Campos originales (BillForm) ---
            "consumo_kwh": _safe_int(raw.get("consumo_total")),
            "lectura_anterior": _safe_int(raw.get("lectura_anterior")),
            "lectura_actual": _safe_int(raw.get("lectura_actual")),
            "total_recibo_mxn": _safe_float(raw.get("total_pagar")),
            "tarifa": tarifa,
            "subsidio_mxn": _safe_float(raw.get("subsidio")),
            "multiplicador": _safe_int(raw.get("multiplicador")) or 1,
            "periodo_inicio": periodo_inicio,  # "YYYY-MM-DD" o None
            "periodo_fin": periodo_fin,        # "YYYY-MM-DD" o None

            # --- Campos de escalones tarifarios (dashboard) ---
            "periodo_basico_kwh": _safe_int(raw.get("periodo_basico_kwh")),
            "periodo_intermedio_kwh": _safe_int(raw.get("periodo_intermedio_kwh")),
            "periodo_excedente_kwh": _safe_int(raw.get("periodo_excedente_kwh")),
            "subtotal_basico_mxn": _safe_float(raw.get("subtotal_basico_mxn")),
            "subtotal_intermedio_mxn": _safe_float(raw.get("subtotal_intermedio_mxn")),
            "subtotal_excedente_mxn": _safe_float(raw.get("subtotal_excedente_mxn")),
        }


# ----------------------------------------------------------------------
# Funciones auxiliares (módulo-level para facilitar el testing)
# ----------------------------------------------------------------------

_TARIFA_VALIDAS = {"1", "1A", "1B", "1C", "1D", "1E", "1F", "DAC"}


def _normalize_tarifa(valor: str) -> Optional[str]:
    """Normaliza el valor de tarifa al formato esperado por el modelo."""
    limpio = valor.strip().upper()
    # Quita prefijos como "TARIFA " que puede dejar el modelo
    limpio = re.sub(r"^TARIFA\s*", "", limpio)
    if limpio in _TARIFA_VALIDAS:
        return limpio
    return None  # No reconocida → el form quedará vacío en ese campo


def _parse_periodo(texto: Optional[str]) -> tuple:
    """
    Parsea un string de periodo tipo "01/12/2024 - 31/01/2025"
    y retorna (inicio_iso, fin_iso).  Si no se puede parsear, (None, None).

    Soporta separadores: " - ", " al ", " a ".
    Soporta formatos de fecha: dd/mm/yyyy, dd-mm-yyyy, yyyy-mm-dd.
    """
    if not texto:
        return None, None

    # Intentar separar en dos fechas.
    # El guión como separador requiere espacios a ambos lados (" - ")
    # para no confundirse con guiones dentro de fechas como "01-12-2024".
    partes = re.split(r"\s+(?:-|al|a)\s+", texto.strip(), maxsplit=1)
    if len(partes) != 2:
        return None, None

    inicio = _parse_fecha(partes[0].strip())
    fin = _parse_fecha(partes[1].strip())
    return inicio, fin


def _parse_fecha(texto: str) -> Optional[str]:
    """Intenta parsear una fecha en varios formatos y retorna ISO (YYYY-MM-DD)."""
    formatos = [
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%d/%m/%y",
        "%d-%m-%y",
    ]
    for fmt in formatos:
        try:
            dt = datetime.strptime(texto, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _safe_int(valor) -> Optional[int]:
    """Convierte a int de forma segura; retorna None si no es posible."""
    if valor is None:
        return None
    try:
        return int(float(valor))  # maneja "280.0" → 280
    except (ValueError, TypeError):
        return None


def _safe_float(valor) -> Optional[float]:
    """Convierte a float de forma segura; retorna None si no es posible."""
    if valor is None:
        return None
    try:
        return round(float(valor), 2)
    except (ValueError, TypeError):
        return None