"""
Vista para extraer datos de un recibo CFE mediante OCR.

POST /extract-bill/
  Content-Type: multipart/form-data
  Campos:
    - evidencia_archivo: imagen del recibo (jpg/jpeg/png/pdf)

Retorna JSON:
  { "ok": true,  "data": { ...campos mapeados... } }
  { "ok": false, "error": "mensaje" }
"""

import os
import json

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt  # HTMX envía CSRF por header; lo dejamos por si alguien testa con curl

from .services.ocr import CFEVisionExtractor


# Extensiones permitidas para la imagen
_EXTENSIONES_OK = {".jpg", ".jpeg", ".png"}

# Tamaño máximo: 5 MB
_MAX_SIZE_BYTES = 5 * 1024 * 1024


@require_POST
def extract_bill(request):
    """
    Endpoint HTMX: recibe una imagen, la envía a OpenAI y retorna
    los campos extraídos como JSON para pre-rellenar el formulario.
    """
    # --- Validar archivo ---
    archivo = request.FILES.get("evidencia_archivo")
    if not archivo:
        return JsonResponse({"ok": False, "error": "No se envió imagen."}, status=400)

    ext = os.path.splitext(archivo.name)[1].lower()
    if ext not in _EXTENSIONES_OK:
        return JsonResponse(
            {"ok": False, "error": f"Formato no soportado ({ext}). Use JPG o PNG."},
            status=400,
        )

    if archivo.size > _MAX_SIZE_BYTES:
        return JsonResponse(
            {"ok": False, "error": "El archivo excede 5 MB."},
            status=400,
        )

    # --- Llamar al extractor ---
    api_key = _get_api_key()
    if not api_key:
        return JsonResponse(
            {"ok": False, "error": "OCR no configurado (falta OPENAI_API_KEY)."},
            status=503,
        )

    mime = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"

    try:
        extractor = CFEVisionExtractor(api_key=api_key)
        datos = extractor.extract_from_bytes(archivo.read(), mime=mime)
    except Exception as exc:  # pragma: no cover
        return JsonResponse(
            {"ok": False, "error": f"Error al procesar imagen: {str(exc)}"},
            status=500,
        )

    return JsonResponse({"ok": True, "data": datos})


def _get_api_key() -> str | None:
    """Obtiene la clave de OpenAI de variables de entorno."""
    return os.environ.get("OPENAI_API_KEY")