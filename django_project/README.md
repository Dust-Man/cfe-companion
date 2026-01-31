# Asistente de Consumo Eléctrico Doméstico - MVP

Sistema para analizar recibos de CFE (México) y obtener recomendaciones de ahorro energético.

## Stack

- Django 5.x
- HTMX (wizard sin recargas)
- Tailwind CSS (via CDN)
- SQLite

## Instalación

```bash
# Crear entorno virtual
python -m venv .venv

# Activar (Linux/Mac)
source .venv/bin/activate
# Activar (Windows)
.venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Crear base de datos
python manage.py migrate

# Cargar datos de demo
python manage.py seed_demo

# Ejecutar servidor
python manage.py runserver
```

## Uso

1. Acceder a http://localhost:8000
2. Click en "Analizar mi recibo" o usar "Modo demo"
3. Completar datos del recibo (manual)
4. Responder cuestionario de hogar
5. Ver resultados y recomendaciones

## Modo Demo

Hay 2 recibos pre-cargados:
- **Ejemplo 1**: 280 kWh, tarifa 1C, 4 personas, sin A/C
- **Ejemplo 2**: 800 kWh, DAC, 2 A/C, alta demanda

## Tests

```bash
python manage.py test energy.tests
```

## Estructura

```
electric_assistant/
├── manage.py
├── electric_assistant/     # Proyecto Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── energy/                 # App principal
    ├── models.py           # Bill, Survey, AnalysisResult
    ├── forms.py            # BillForm, SurveyForm
    ├── views.py            # Vistas del wizard
    ├── urls.py             # Rutas
    ├── services/           # Lógica de cálculo
    │   └── calculations.py
    ├── templates/energy/   # Templates con HTMX
    └── management/commands/
        └── seed_demo.py    # Datos de ejemplo
```

## Notas

- Los cálculos son **estimaciones** basadas en reglas heurísticas
- No sustituyen medición real de consumo
- Las tarifas CFE son aproximadas (2024)
