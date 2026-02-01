"""
Views for the Electric Assistant MVP.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods

from .models import Bill, Survey, AnalysisResult
from .forms import BillForm
from .services.calculations import compute_cost_mxn, compute_co2e_kg
from .services.recommendations import get_recommendations


# ─── Choice tuples used by the new survey template ──────────────────────────
SURVEY_CHOICES = {
    # 2 — A/C
    'ac_choices': [
        ('no', 'No'),
        ('minisplit_inverter', 'Sí, minisplit inverter'),
        ('minisplit_no_inverter', 'Sí, minisplit no inverter'),
        ('ventana', 'Sí, de ventana'),
        ('no_se', 'Sí, no sé cuál'),
    ],
    'ac_unidades_choices': [('1', '1'), ('2', '2'), ('3+', '3+')],
    'ac_dias_choices': [('1-2', '1–2'), ('3-4', '3–4'), ('5-6', '5–6'), ('7', '7')],
    'ac_horas_choices': [('1-2', '1–2 h'), ('3-5', '3–5 h'), ('6-8', '6–8 h'), ('9+', '9+ h')],
    'ac_temp_choices': [('18-20', '18–20°C'), ('21-23', '21–23°C'), ('24-26', '24–26°C'), ('no_se', 'No sé')],

    # 3 — Agua caliente
    'agua_tipo_choices': [('gas', 'Gas (boiler de gas)'), ('electrico', 'Eléctrico'), ('mixto', 'Mixto / no sé')],
    'agua_equipo_choices': [
        ('boiler_electrico', 'Boiler eléctrico (tanque)'),
        ('regadera_electrica', 'Regadera eléctrica instantánea'),
        ('ambos', 'Ambos'),
        ('no_se', 'No sé'),
    ],
    'agua_personas_choices': [('1', '1'), ('2', '2'), ('3-4', '3–4'), ('5+', '5+')],
    'agua_duracion_choices': [('3-5', '3–5 min'), ('6-10', '6–10 min'), ('11-15', '11–15 min'), ('16+', '16+ min')],

    # 4 — Refrigeración
    'ref_count_choices': [('0', '0'), ('1', '1'), ('2', '2'), ('3+', '3+')],
    'ref_antiguedad_choices': [
        ('nuevo', 'Nuevo (0–5 años)'),
        ('medio', 'Medio (6–10 años)'),
        ('viejo', 'Viejo (11+ años)'),
        ('no_se', 'No sé'),
    ],

    # 5 — Secadora
    'secadora_choices': [('no', 'No'), ('electrica', 'Sí, eléctrica'), ('gas', 'Sí, gas'), ('no_se', 'No sé')],
    'secadora_cargas_choices': [('1-2', '1–2'), ('3-4', '3–4'), ('5-7', '5–7'), ('8+', '8+')],
    'secadora_calor_choices': [('si', 'Sí'), ('no', 'No'), ('no_se', 'No sé')],

    # 6 — Bombas
    'bomba_choices': [('no', 'No'), ('si', 'Sí'), ('no_se', 'No sé')],
    'bomba_frecuencia_choices': [
        ('poco', 'Poco (solo cuando se usa agua)'),
        ('normal', 'Normal (varias veces/día)'),
        ('mucho', 'Mucho (casi siempre)'),
        ('no_se', 'No sé'),
    ],
    'bomba_alberca_choices': [('no', 'No'), ('si', 'Sí')],
    'bomba_alberca_horas_choices': [('1-2', '1–2 h'), ('3-5', '3–5 h'), ('6+', '6+ h')],

    # 7 — Calefactor
    'calefactor_choices': [
        ('no', 'No'),
        ('ocasional', 'Sí, ocasional (1–3 días/sem)'),
        ('frecuente', 'Sí, frecuente (4–7 días/sem)'),
        ('no_se', 'No sé'),
    ],
    'calefactor_horas_choices': [('1-2', '1–2 h'), ('3-5', '3–5 h'), ('6-8', '6–8 h'), ('9+', '9+ h')],

    # 8 — Cocina
    'cocina_tipo_choices': [('gas', 'Gas'), ('electrica', 'Eléctrica / inducción'), ('mixta', 'Mixta')],
    'cocina_horno_choices': [('no', 'No'), ('1-2', '1–2 veces/sem'), ('3+', '3+ veces/sem')],
    'cocina_airfryer_choices': [('no', 'No'), ('1-3', '1–3 veces/sem'), ('4+', '4+ veces/sem')],
    'cocina_parrilla_choices': [('no', 'No'), ('poco', 'Poco'), ('diario', 'Diario')],
    'cocina_hervidor_choices': [('no', 'No'), ('1-3', '1–3 veces/sem'), ('diario', 'Diario')],

    # 9 — Siempre encendidos
    'tvs_choices': [('0', '0'), ('1', '1'), ('2', '2'), ('3+', '3+')],
    'pc_choices': [('no', 'No'), ('1-3', 'Sí (1–3 h/día)'), ('4-8', 'Sí (4–8 h/día)'), ('9+', 'Sí (9+ h/día)')],
    'consola_choices': [('no', 'No'), ('1-3', 'Sí (1–3 h/día)'), ('4+', 'Sí (4+ h/día)')],
    'siempre_encendidos_choices': [
        ('router', 'Router/modem siempre prendido'),
        ('camaras', 'Cámaras / NVR'),
        ('servidor', 'Servidor / NAS'),
    ],

    # 10 — Culpables ocultos
    'culpables_choices': [
        ('lavavajillas', 'Lavavajillas'),
        ('deshumidificador', 'Deshumidificador'),
        ('enfriador_aire', 'Enfriador de aire (cooler / aire lavado)'),
        ('dispensador_agua', 'Dispensador / enfriador de agua'),
        ('acuario', 'Acuario grande / terrario con calentador'),
        ('herramientas_taller', 'Herramientas de taller (compresor, soldadora)'),
        ('vehiculo_electrico', 'Carga de vehículo eléctrico / bici eléctrica frecuente'),
    ],
    'culpables_uso_choices': [
        ('solo_a_veces', 'Solo a veces'),
        ('1-2', '1–2 h/día'),
        ('3-5', '3–5 h/día'),
        ('6+', '6+ h/día'),
        ('no_se', 'No sé'),
    ],
}


def _parse_survey_post(post) -> dict:
    """
    Parsea el POST de la nueva encuesta condicional y retorna
    el dict `respuestas` listo para guardar en Survey.respuestas.
    """
    r = {}

    # 1. Cambios recientes (checkbox multiple)
    r['cambios_recientes'] = post.getlist('cambios_recientes')

    # 2. A/C
    r['tiene_ac'] = post.get('tiene_ac', 'no')
    if r['tiene_ac'] != 'no':
        r['ac_unidades'] = post.get('ac_unidades', '')
        r['ac_dias_semana'] = post.get('ac_dias_semana', '')
        r['ac_horas_dia'] = post.get('ac_horas_dia', '')
        r['ac_temperatura'] = post.get('ac_temperatura', '')

    # 3. Agua caliente
    r['agua_caliente_tipo'] = post.get('agua_caliente_tipo', 'gas')
    if r['agua_caliente_tipo'] in ('electrico', 'mixto'):
        r['agua_caliente_equipo'] = post.getlist('agua_caliente_equipo')
        r['agua_personas'] = post.get('agua_personas', '')
        r['agua_duracion'] = post.get('agua_duracion', '')

    # 4. Refrigeración
    r['refrigeradores'] = post.get('refrigeradores', '1')
    if r['refrigeradores'] != '0':
        r['ref_antiguedad'] = post.get('ref_antiguedad', 'no_se')

    # 5. Secadora
    r['tiene_secadora'] = post.get('tiene_secadora', 'no')
    if r['tiene_secadora'] == 'electrica':
        r['secadora_cargas'] = post.get('secadora_cargas', '')
        r['secadora_alto_calor'] = post.get('secadora_alto_calor', '')

    # 6. Bombas
    r['tiene_bomba'] = post.get('tiene_bomba', 'no')
    if r['tiene_bomba'] == 'si':
        r['bomba_frecuencia'] = post.get('bomba_frecuencia', '')
    r['tiene_bomba_alberca'] = post.get('tiene_bomba_alberca', 'no')
    if r['tiene_bomba_alberca'] == 'si':
        r['bomba_alberca_horas'] = post.get('bomba_alberca_horas', '')

    # 7. Calefactor
    r['calefactor'] = post.get('calefactor', 'no')
    if r['calefactor'] in ('ocasional', 'frecuente'):
        r['calefactor_horas'] = post.get('calefactor_horas', '')

    # 8. Cocina
    r['cocina_tipo'] = post.get('cocina_tipo', 'gas')
    r['cocina_horno'] = post.get('cocina_horno', 'no')
    r['cocina_airfryer'] = post.get('cocina_airfryer', 'no')
    r['cocina_parrilla'] = post.get('cocina_parrilla', 'no')
    r['cocina_hervidor'] = post.get('cocina_hervidor', 'no')

    # 9. Siempre encendidos
    r['tvs'] = post.get('tvs', '0')
    r['pc_uso'] = post.get('pc_uso', 'no')
    r['consola'] = post.get('consola', 'no')
    r['siempre_encendidos'] = post.getlist('siempre_encendidos')

    # 10. Culpables ocultos
    r['culpables_ocultos'] = post.getlist('culpables_ocultos')
    if r['culpables_ocultos']:
        r['culpables_uso'] = post.get('culpables_uso', '')

    return r


# ─── VIEWS ───────────────────────────────────────────────────────────────────

def home(request):
    """Página principal."""
    demo_bills = Bill.objects.filter(is_demo=True).order_by('id')[:2]
    return render(request, 'energy/home.html', {
        'demo_bills': demo_bills,
        'has_demos': demo_bills.exists(),
    })


def new_bill(request):
    """Inicia el wizard con el formulario de recibo."""
    form = BillForm()
    context = {'form': form, 'step': 1, 'total_steps': 3}
    if request.htmx:
        return render(request, 'energy/partials/bill_form.html', context)
    return render(request, 'energy/wizard.html', context)


@require_http_methods(["POST"])
def create_bill(request):
    """Crea el recibo y redirige al dashboard."""
    form = BillForm(request.POST, request.FILES)

    if form.is_valid():
        bill = form.save()

        # Guardar en historial de sesión
        if 'bill_history' not in request.session:
            request.session['bill_history'] = []
        request.session['bill_history'] = [bill.id] + request.session['bill_history'][:4]
        request.session.modified = True

        # Redirigir al dashboard
        if request.htmx:
            response = HttpResponse()
            response['HX-Redirect'] = f'/dashboard/{bill.id}/'
            return response
        return redirect('energy:dashboard', bill_id=bill.id)

    # Errores
    context = {'form': form, 'step': 1, 'total_steps': 3}
    if request.htmx:
        return render(request, 'energy/partials/bill_form.html', context)
    return render(request, 'energy/wizard.html', context)


def survey(request, bill_id):
    """Maneja GET (mostrar encuesta) y POST (guardar + redirigir a resultados)."""
    bill = get_object_or_404(Bill, id=bill_id)

    if request.method == 'POST':
        respuestas = _parse_survey_post(request.POST)
        Survey.objects.update_or_create(
            bill=bill,
            defaults={'respuestas': respuestas}
        )

        # Redirigir a resultados
        if request.htmx:
            response = HttpResponse()
            response['HX-Redirect'] = f'/results/{bill.id}/'
            return response
        return redirect('energy:results', bill_id=bill.id)

    # GET — mostrar encuesta
    context = {**SURVEY_CHOICES, 'bill': bill, 'step': 2, 'total_steps': 3}
    if request.htmx:
        return render(request, 'energy/partials/survey_form.html', context)
    return render(request, 'energy/wizard.html', context)


def results(request, bill_id):
    """Obtiene recomendaciones de OpenAI y las muestra."""
    bill = get_object_or_404(Bill, id=bill_id)

    # Verificar que exista el survey
    try:
        survey_obj = bill.survey
    except Survey.DoesNotExist:
        return redirect('energy:survey', bill_id=bill.id)

    respuestas = survey_obj.respuestas

    # ── Obtener o generar recomendaciones ──
    # Guardamos en AnalysisResult.recomendaciones_json para no llamar a OpenAI
    # cada vez que el usuario refresca la página.
    try:
        analysis = bill.analysis
        recs = analysis.recomendaciones_json
    except AnalysisResult.DoesNotExist:
        # Llamar a OpenAI
        try:
            recs = get_recommendations(respuestas, bill.tarifa, bill.consumo_kwh)
        except Exception as exc:
            # Fallback: mostrar error amable
            recs = []
            # Podrías logear exc aquí

        # Guardar para evitar llamadas repetidas
        costo = compute_cost_mxn(bill.consumo_kwh, bill.tarifa)
        co2e = compute_co2e_kg(bill.consumo_kwh)
        AnalysisResult.objects.create(
            bill=bill,
            costo_estimado_mxn=costo,
            co2e_kg=co2e,
            recomendaciones_json=recs,
        )

    # ── Separar por tipo ──
    recs_sin = [r for r in recs if r.get('tipo') == 'sin_inversion']
    recs_con = [r for r in recs if r.get('tipo') == 'con_inversion']

    # ── Totales para el summary strip ──
    total_ahorro_anual = sum(r.get('ahorro_anual_mxn', 0) for r in recs)
    total_co2 = sum(r.get('reduccion_co2_kg_anual', 0) for r in recs)

    context = {
        'bill': bill,
        'recs_sin_inversion': recs_sin,
        'recs_con_inversion': recs_con,
        'total_ahorro_anual': total_ahorro_anual,
        'total_co2': total_co2,
    }
    return render(request, 'energy/results.html', context)


def dashboard(request, bill_id):
    """Dashboard del recibo (sin cambios)."""
    bill = get_object_or_404(Bill, id=bill_id)

    total_consumo = bill.consumo_kwh
    if bill.consumo_excedente > 0:
        basico_pct = 100.0
        intermedio_pct = 100.0
        excedente_pct = (bill.consumo_excedente / total_consumo * 100) if total_consumo > 0 else 0
    elif bill.consumo_intermedio > 0:
        basico_pct = 100.0
        intermedio_pct = (bill.consumo_intermedio / 130 * 100) if bill.consumo_intermedio > 0 else 0
        excedente_pct = 0
    else:
        basico_pct = (bill.consumo_basico / 150 * 100) if bill.consumo_basico > 0 else 0
        intermedio_pct = 0
        excedente_pct = 0

    return render(request, 'energy/dashboard.html', {
        'bill': bill,
        'basico_pct': basico_pct,
        'intermedio_pct': intermedio_pct,
        'excedente_pct': excedente_pct,
    })


def load_demo(request, demo_id):
    """Carga un recibo demo y muestra resultados."""
    demo_bill = get_object_or_404(Bill, id=demo_id, is_demo=True)
    try:
        _ = demo_bill.survey
    except Survey.DoesNotExist:
        return redirect('energy:home')
    return redirect('energy:results', bill_id=demo_bill.id)


def history(request):
    """Historial de análisis recientes."""
    bill_ids = request.session.get('bill_history', [])
    bills = Bill.objects.filter(id__in=bill_ids, is_demo=False).order_by('-created_at')[:5]

    context = {'bills': bills}
    if request.htmx:
        return render(request, 'energy/partials/history_list.html', context)
    return render(request, 'energy/history.html', context)