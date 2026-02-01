"""
Views for the Electric Assistant MVP.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.views.decorators.http import require_http_methods

from .models import Bill, Survey, AnalysisResult
from .forms import BillForm, SurveyForm
from .services.calculations import compute_cost_mxn, compute_co2e_kg, compute_breakdown_and_recs


def home(request):
    """Página principal con CTA y modo demo."""
    # Verificar si hay demos disponibles
    demo_bills = Bill.objects.filter(is_demo=True).order_by('id')[:2]
    
    context = {
        'demo_bills': demo_bills,
        'has_demos': demo_bills.exists(),
    }
    return render(request, 'energy/home.html', context)


def new_bill(request):
    """Inicia el wizard con el formulario de recibo."""
    form = BillForm()
    context = {
        'form': form,
        'step': 1,
        'total_steps': 3,
    }
    
    # Si es HTMX, devolver solo el partial
    if request.htmx:
        return render(request, 'energy/partials/bill_form.html', context)
    
    return render(request, 'energy/wizard.html', context)


@require_http_methods(["POST"])
def create_bill(request):
    """Crea el recibo y avanza al cuestionario."""
    form = BillForm(request.POST, request.FILES)
    
    if form.is_valid():
        bill = form.save()
        
        # Guardar ID en sesión para historial
        if 'bill_history' not in request.session:
            request.session['bill_history'] = []
        request.session['bill_history'] = [bill.id] + request.session['bill_history'][:4]
        request.session.modified = True
        
        # Devolver formulario de survey via HTMX
        survey_form = SurveyForm()
        context = {
            'form': survey_form,
            'bill': bill,
            'step': 2,
            'total_steps': 3,
        }
        
        if request.htmx:
            return render(request, 'energy/partials/survey_form.html', context)
        
        return redirect('energy:survey', bill_id=bill.id)
    
    # Si hay errores, mostrar de nuevo el formulario
    context = {
        'form': form,
        'step': 1,
        'total_steps': 3,
    }
    
    if request.htmx:
        return render(request, 'energy/partials/bill_form.html', context)
    
    return render(request, 'energy/wizard.html', context)


def survey(request, bill_id):
    """Formulario del cuestionario de hogar."""
    bill = get_object_or_404(Bill, id=bill_id)
    
    if request.method == 'POST':
        form = SurveyForm(request.POST)
        if form.is_valid():
            survey_obj = form.save(commit=False)
            survey_obj.bill = bill
            survey_obj.save()
            
            # Redirigir a resultados
            if request.htmx:
                response = HttpResponse()
                response['HX-Redirect'] = f'/results/{bill.id}/'
                return response
            
            return redirect('energy:results', bill_id=bill.id)
    else:
        form = SurveyForm()
    
    context = {
        'form': form,
        'bill': bill,
        'step': 2,
        'total_steps': 3,
    }
    
    if request.htmx:
        return render(request, 'energy/partials/survey_form.html', context)
    
    return render(request, 'energy/wizard.html', context)


def results(request, bill_id):
    """Muestra resultados del análisis."""
    bill = get_object_or_404(Bill, id=bill_id)
    
    # Verificar que exista el survey
    try:
        survey_obj = bill.survey
    except Survey.DoesNotExist:
        return redirect('energy:survey', bill_id=bill.id)
    
    # Calcular o recuperar resultados
    try:
        analysis = bill.analysis
    except AnalysisResult.DoesNotExist:
        # Calcular
        costo = compute_cost_mxn(bill.consumo_kwh, bill.tarifa)
        co2e = compute_co2e_kg(bill.consumo_kwh)
        calc_result = compute_breakdown_and_recs(bill, survey_obj)
        
        analysis = AnalysisResult.objects.create(
            bill=bill,
            costo_estimado_mxn=costo,
            co2e_kg=co2e,
            breakdown_json=calc_result['breakdown'],
            recomendaciones_json=calc_result['recomendaciones'],
            supuestos_json=calc_result['supuestos'],
            confianza_global=calc_result['confianza_global']
        )
    
    # Ordenar breakdown para display
    breakdown_sorted = sorted(
        analysis.breakdown_json.items(),
        key=lambda x: x[1]['kwh'],
        reverse=True
    )
    
    context = {
        'bill': bill,
        'survey': survey_obj,
        'analysis': analysis,
        'breakdown_sorted': breakdown_sorted,
        'step': 3,
        'total_steps': 3,
    }
    
    return render(request, 'energy/results.html', context)

def dashboard(request, bill_id):
    """Muestra un dashboard con métricas clave del recibo."""
    bill = get_object_or_404(Bill, id=bill_id)
    
    # Calculate stacked percentages for progress bars
    # Basic bar is 100% only when consumption exceeds basic tier (goes to intermediate)
    total_consumo = bill.consumo_kwh
    
    if bill.consumo_excedente > 0:
        # When there's excess consumption, basic and intermediate tiers are 100% full
        basico_pct = 100.0
        intermedio_pct = 100.0
        excedente_pct = (bill.consumo_excedente / total_consumo * 100) if total_consumo > 0 else 0
    elif bill.consumo_intermedio > 0:
        # Has intermediate consumption but no excess: basic is 100%, intermediate shows actual %
        basico_pct = 100.0
        intermedio_pct = (bill.consumo_intermedio / 130 * 100) if bill.consumo_intermedio > 0 else 0  # Max intermediate is 130 kWh
        excedente_pct = 0
    else:
        # Only basic consumption: show actual percentage of basic tier
        basico_pct = (bill.consumo_basico / 150 * 100) if bill.consumo_basico > 0 else 0  # Max basic is 150 kWh
        intermedio_pct = 0
        excedente_pct = 0
    
    context = {
        'bill': bill,
        'basico_pct': basico_pct,
        'intermedio_pct': intermedio_pct,
        'excedente_pct': excedente_pct,
    }
    
    return render(request, 'energy/dashboard.html', context)
def load_demo(request, demo_id):
    """Carga un recibo demo y muestra resultados."""
    demo_bill = get_object_or_404(Bill, id=demo_id, is_demo=True)
    
    # Verificar que tenga survey
    try:
        _ = demo_bill.survey
    except Survey.DoesNotExist:
        return redirect('energy:home')
    
    return redirect('energy:results', bill_id=demo_bill.id)


def history(request):
    """Muestra historial de análisis recientes."""
    bill_ids = request.session.get('bill_history', [])
    bills = Bill.objects.filter(id__in=bill_ids, is_demo=False).order_by('-created_at')[:5]
    
    context = {
        'bills': bills,
    }
    
    if request.htmx:
        return render(request, 'energy/partials/history_list.html', context)
    
    return render(request, 'energy/history.html', context)
