
# Plan: Implementacion OCR con Procesamiento Asincrono y Validacion Manual

## Resumen

Implementaremos un sistema de OCR opcional para extraer datos de recibos CFE que incluye:

- **Procesamiento asincrono**: Feedback visual durante la extraccion (puede tomar 5-30 segundos)
- **Validacion manual**: El usuario revisa los datos extraidos antes de aplicarlos al formulario
- **Manejo de errores robusto**: Mensajes claros cuando el OCR falle parcial o totalmente

El enfoque "manual-first" se mantiene: el OCR es una ayuda, no un requisito.

---

## Flujo de Usuario Actualizado

```text
+----------------+     +------------------+     +-------------------+
|  Usuario sube  | --> |  Pantalla de     | --> |  Modal/Panel de   |
|  archivo       |     |  procesamiento   |     |  validacion       |
+----------------+     +------------------+     +-------------------+
                              |                         |
                              v                         v
                       (spinner + mensajes)     (revisar/corregir/aplicar)
                                                        |
                                                        v
                                                +------------------+
                                                | Formulario pre-  |
                                                | llenado          |
                                                +------------------+
```

**Estados del proceso:**
1. **Inicial**: Boton "Subir recibo para extraccion automatica"
2. **Procesando**: Spinner animado + mensajes de progreso
3. **Validacion**: Panel con datos extraidos + campos editables + badges de confianza
4. **Aplicado**: Formulario pre-llenado con datos confirmados
5. **Error**: Mensaje descriptivo + opcion de reintentar o continuar manual

---

## Arquitectura Tecnica

### 1. Nuevo Servicio: `energy/services/ocr.py`

```python
# Estructura principal del servicio

class OCRResult:
    """Resultado del procesamiento OCR."""
    success: bool
    fields: dict          # Campos extraidos con valores
    confidence: dict      # Nivel de confianza por campo
    warnings: list        # Advertencias (campos no encontrados)
    error_message: str    # Mensaje si fallo completamente

def extract_text_from_file(file) -> tuple[str, str]:
    """
    Extrae texto de imagen o PDF.
    Returns: (texto_extraido, tipo_archivo)
    Raises: OCRProcessingError si falla
    """

def parse_cfe_bill(raw_text: str) -> OCRResult:
    """
    Parsea el texto usando patrones regex para campos CFE.
    Siempre retorna resultado (puede tener campos vacios).
    """
```

**Patrones de extraccion:**

| Campo | Patron Regex | Confianza |
|-------|-------------|-----------|
| Tarifa | `TARIFA[:\s]*([1][A-F]?\|DAC)` | Alta si match exacto |
| kWh | `(\d{1,4})\s*kWh` | Alta si unico match |
| Total MXN | `TOTAL.*?\$?\s*([\d,]+\.\d{2})` | Media (multiples totales posibles) |
| Periodo | `(\d{2}[/-]\w{3}[/-]\d{4})` | Media (formato variable) |
| Lecturas | `LECTURA\s*(ANTERIOR\|ACTUAL).*?(\d+)` | Baja (OCR puede fallar en numeros) |

**Manejo de errores en el servicio:**

```python
class OCRError(Exception):
    """Error base para OCR."""
    pass

class FileTypeError(OCRError):
    """Tipo de archivo no soportado."""
    message = "Solo se aceptan archivos PDF, JPG o PNG"

class ExtractionError(OCRError):
    """Error durante la extraccion de texto."""
    message = "No se pudo procesar el archivo. Intenta con mejor calidad."

class NoDataFoundError(OCRError):
    """No se encontraron datos en el texto."""
    message = "No se encontraron datos de recibo CFE en la imagen."
```

---

### 2. Nueva Vista Asincrona: `views.py`

```python
@require_http_methods(["POST"])
def process_ocr(request):
    """
    Procesa archivo subido con OCR.
    Retorna partial HTML con resultados para validacion.
    """
    try:
        archivo = request.FILES.get('archivo_ocr')
        
        # Validaciones iniciales
        if not archivo:
            return render(request, 'energy/partials/ocr_error.html', {
                'error_type': 'no_file',
                'message': 'No se recibio ningun archivo'
            })
        
        # Validar tipo y tamano
        if archivo.size > 10 * 1024 * 1024:  # 10MB max
            return render(request, 'energy/partials/ocr_error.html', {
                'error_type': 'file_too_large',
                'message': 'El archivo es muy grande (max 10MB)'
            })
        
        # Procesar OCR
        result = process_bill_ocr(archivo)
        
        if result.success:
            return render(request, 'energy/partials/ocr_validation.html', {
                'fields': result.fields,
                'confidence': result.confidence,
                'warnings': result.warnings
            })
        else:
            return render(request, 'energy/partials/ocr_error.html', {
                'error_type': 'extraction_failed',
                'message': result.error_message,
                'can_retry': True
            })
            
    except Exception as e:
        return render(request, 'energy/partials/ocr_error.html', {
            'error_type': 'unexpected',
            'message': 'Error inesperado. Por favor intenta de nuevo.',
            'can_retry': True
        })
```

---

### 3. Nuevos Templates Parciales

#### `partials/ocr_upload.html` - Seccion de subida

Contiene el boton de subida y el area donde aparecera el resultado.

```html
<!-- Seccion de OCR al inicio del formulario -->
<div id="ocr-section" class="mb-6">
    <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 class="font-semibold text-blue-800 mb-2">
            Extraccion automatica (opcional)
        </h3>
        <p class="text-sm text-blue-600 mb-4">
            Sube una foto o PDF de tu recibo para extraer los datos automaticamente.
        </p>
        
        <form hx-post="/ocr/process/" 
              hx-target="#ocr-result"
              hx-swap="innerHTML"
              hx-indicator="#ocr-loading"
              enctype="multipart/form-data">
            {% csrf_token %}
            
            <input type="file" 
                   name="archivo_ocr"
                   accept=".pdf,.jpg,.jpeg,.png"
                   class="..." />
            
            <button type="submit" class="...">
                Extraer datos
            </button>
        </form>
        
        <!-- Indicador de carga (oculto por defecto) -->
        <div id="ocr-loading" class="htmx-indicator">
            <!-- Animacion de procesamiento -->
        </div>
        
        <!-- Resultado del OCR (se llena via HTMX) -->
        <div id="ocr-result"></div>
    </div>
</div>
```

#### `partials/ocr_processing.html` - Estado de procesamiento

Mostrado mientras el OCR trabaja (via htmx-indicator).

```html
<div class="text-center py-6">
    <svg class="animate-spin h-10 w-10 text-blue-500 mx-auto mb-4">...</svg>
    <p class="text-gray-700 font-medium">Procesando tu recibo...</p>
    <p class="text-sm text-gray-500 mt-2">
        Esto puede tomar unos segundos
    </p>
</div>
```

#### `partials/ocr_validation.html` - Panel de validacion (NUEVO)

Panel que muestra los datos extraidos para que el usuario revise y confirme.

```html
<div class="bg-green-50 border border-green-300 rounded-lg p-4 mt-4">
    <div class="flex items-center justify-between mb-4">
        <h4 class="font-semibold text-green-800">
            Datos detectados
        </h4>
        <span class="text-xs text-green-600">
            Revisa antes de aplicar
        </span>
    </div>
    
    <!-- Campos extraidos con edicion inline -->
    <div class="space-y-3">
        {% for field_name, field_data in fields.items %}
        <div class="flex items-center justify-between bg-white p-2 rounded">
            <div class="flex items-center gap-2">
                <span class="text-sm font-medium text-gray-700">
                    {{ field_data.label }}:
                </span>
                <input type="text" 
                       name="ocr_{{ field_name }}"
                       value="{{ field_data.value }}"
                       class="border rounded px-2 py-1 text-sm w-32" />
            </div>
            
            <!-- Badge de confianza -->
            <span class="text-xs px-2 py-1 rounded-full
                {% if field_data.confidence == 'high' %}
                    bg-green-100 text-green-700
                {% elif field_data.confidence == 'medium' %}
                    bg-yellow-100 text-yellow-700  
                {% else %}
                    bg-red-100 text-red-700
                {% endif %}">
                {{ field_data.confidence_label }}
            </span>
        </div>
        {% endfor %}
    </div>
    
    <!-- Advertencias (campos no encontrados) -->
    {% if warnings %}
    <div class="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded">
        <p class="text-sm text-yellow-700">
            No se detectaron: {{ warnings|join:", " }}
        </p>
    </div>
    {% endif %}
    
    <!-- Botones de accion -->
    <div class="mt-4 flex gap-3">
        <button type="button" 
                onclick="applyOCRData()"
                class="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">
            Aplicar al formulario
        </button>
        <button type="button"
                onclick="clearOCRResult()"
                class="bg-gray-200 text-gray-700 px-4 py-2 rounded hover:bg-gray-300">
            Descartar
        </button>
    </div>
</div>
```

#### `partials/ocr_error.html` - Estado de error

```html
<div class="bg-red-50 border border-red-200 rounded-lg p-4 mt-4">
    <div class="flex items-start gap-3">
        <svg class="w-6 h-6 text-red-500 flex-shrink-0">...</svg>
        <div>
            <h4 class="font-semibold text-red-800">
                {% if error_type == 'no_file' %}
                    No se recibio archivo
                {% elif error_type == 'file_too_large' %}
                    Archivo muy grande
                {% elif error_type == 'unsupported_type' %}
                    Tipo de archivo no soportado
                {% elif error_type == 'extraction_failed' %}
                    No se pudo extraer informacion
                {% else %}
                    Error inesperado
                {% endif %}
            </h4>
            <p class="text-sm text-red-600 mt-1">{{ message }}</p>
            
            {% if can_retry %}
            <button type="button" 
                    onclick="resetOCRUpload()"
                    class="mt-3 text-sm text-red-700 underline hover:no-underline">
                Intentar con otro archivo
            </button>
            {% endif %}
            
            <p class="text-xs text-gray-500 mt-2">
                Puedes continuar llenando el formulario manualmente.
            </p>
        </div>
    </div>
</div>
```

---

### 4. JavaScript para Validacion Manual

Agregar al template base o como bloque extra_js.

```javascript
// Aplicar datos del OCR al formulario principal
function applyOCRData() {
    const ocrFields = document.querySelectorAll('[name^="ocr_"]');
    
    ocrFields.forEach(field => {
        const targetName = field.name.replace('ocr_', '');
        const targetField = document.querySelector(`[name="${targetName}"]`);
        
        if (targetField && field.value) {
            targetField.value = field.value;
            // Resaltar campo modificado
            targetField.classList.add('ring-2', 'ring-green-300');
            setTimeout(() => {
                targetField.classList.remove('ring-2', 'ring-green-300');
            }, 2000);
        }
    });
    
    // Limpiar seccion OCR
    document.getElementById('ocr-result').innerHTML = `
        <div class="text-green-600 text-sm p-2">
            Datos aplicados. Revisa y corrige si es necesario.
        </div>
    `;
}

// Descartar resultados OCR
function clearOCRResult() {
    document.getElementById('ocr-result').innerHTML = '';
}

// Reiniciar para nuevo intento
function resetOCRUpload() {
    document.getElementById('ocr-result').innerHTML = '';
    document.querySelector('[name="archivo_ocr"]').value = '';
}
```

---

### 5. Actualizacion de URLs

```python
# energy/urls.py
urlpatterns = [
    # ... rutas existentes ...
    path('ocr/process/', views.process_ocr, name='process_ocr'),
]
```

---

### 6. Actualizacion de Dependencias

```text
# requirements.txt (agregar)
pytesseract>=0.3.10
pdf2image>=1.16.0
Pillow>=10.0.0  # ya existe
```

**Dependencias del sistema (documentar en README):**

```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-spa poppler-utils

# macOS
brew install tesseract poppler

# El paquete de idioma espanol mejora la precision
```

---

## Manejo de Errores Detallado

### Tabla de Errores y Respuestas

| Escenario | Codigo | Mensaje Usuario | Accion |
|-----------|--------|-----------------|--------|
| Sin archivo | no_file | "Selecciona un archivo primero" | Resaltar input |
| Archivo > 10MB | file_too_large | "Maximo 10MB. Intenta con menor resolucion" | Limpiar input |
| Tipo invalido | unsupported_type | "Solo PDF, JPG o PNG" | Limpiar input |
| OCR vacio | no_text | "No se pudo leer el archivo. Prueba con mejor iluminacion" | Permitir reintento |
| Sin datos CFE | no_cfe_data | "No parece ser un recibo CFE. Verifica el archivo" | Permitir reintento |
| Datos parciales | partial | Mostrar lo encontrado + advertencias | Validacion con warnings |
| Timeout | timeout | "El proceso tomo mucho tiempo. Intenta con archivo mas pequeno" | Permitir reintento |
| Error sistema | unexpected | "Error inesperado. Por favor intenta de nuevo" | Permitir reintento |

### Logica de Confianza por Campo

```python
def calculate_field_confidence(field_name, value, raw_text):
    """Determina confianza de un campo extraido."""
    
    if not value:
        return 'none'
    
    # Tarifa: alta si coincide exactamente con patron CFE
    if field_name == 'tarifa':
        if value in ['1', '1A', '1B', '1C', '1D', '1E', '1F', 'DAC']:
            return 'high'
        return 'low'
    
    # kWh: alta si solo hay un numero con "kWh" cerca
    if field_name == 'consumo_kwh':
        matches = re.findall(r'\d{1,4}\s*kWh', raw_text, re.I)
        if len(matches) == 1:
            return 'high'
        return 'medium'
    
    # Fechas: media (formatos variables)
    if field_name in ['periodo_inicio', 'periodo_fin']:
        return 'medium'
    
    # Montos: media (pueden haber varios en recibo)
    if field_name in ['total_recibo_mxn', 'subsidio_mxn']:
        return 'medium'
    
    # Lecturas: baja (OCR frecuentemente falla)
    if field_name in ['lectura_anterior', 'lectura_actual']:
        return 'low'
    
    return 'medium'
```

---

## Secuencia de Implementacion

| Paso | Archivo | Descripcion |
|------|---------|-------------|
| 1 | `energy/services/ocr.py` | Servicio completo con extraccion y parsing |
| 2 | `requirements.txt` | Agregar pytesseract y pdf2image |
| 3 | `energy/views.py` | Nueva vista `process_ocr` |
| 4 | `energy/urls.py` | Nueva ruta `/ocr/process/` |
| 5 | `templates/energy/partials/ocr_upload.html` | Seccion de subida |
| 6 | `templates/energy/partials/ocr_validation.html` | Panel de validacion |
| 7 | `templates/energy/partials/ocr_error.html` | Mensajes de error |
| 8 | `templates/energy/partials/bill_form.html` | Integrar seccion OCR |
| 9 | `templates/energy/base.html` | Agregar JavaScript |
| 10 | `README.md` | Documentar instalacion Tesseract |
| 11 | `energy/tests.py` | Tests para parsing y errores |

---

## Consideraciones Adicionales

### Timeout y Archivos Grandes

- Configurar timeout de 30 segundos para el procesamiento
- Archivos PDF multi-pagina: procesar solo primera pagina
- Imagenes muy grandes: redimensionar antes de OCR

### Privacidad

- Archivos se procesan en memoria cuando sea posible
- Archivos temporales se eliminan despues del procesamiento
- No se envian datos a servicios externos

### Accesibilidad

- Mensajes de error claros y descriptivos
- Indicador de progreso visible
- Opcion clara de continuar sin OCR

---

## Notas de Instalacion Actualizadas

Agregar al README:

```markdown
## Requisitos Adicionales para OCR (Opcional)

El OCR requiere Tesseract instalado en el sistema:

### Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-spa poppler-utils

### macOS
brew install tesseract poppler

### Windows
1. Descargar Tesseract de: https://github.com/UB-Mannheim/tesseract/wiki
2. Instalar poppler: https://github.com/oschwartz10612/poppler-windows/releases
3. Agregar ambos al PATH del sistema

Si Tesseract no esta instalado, el sistema funcionara normalmente
pero la extraccion automatica estara deshabilitada.
```
