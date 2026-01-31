"""
Command to seed demo data for the Electric Assistant MVP.
Creates two example bills with surveys and pre-computed analysis.
"""

from datetime import date, timedelta
from django.core.management.base import BaseCommand
from energy.models import Bill, Survey, AnalysisResult
from energy.services.calculations import compute_cost_mxn, compute_co2e_kg, compute_breakdown_and_recs


class Command(BaseCommand):
    help = 'Seeds the database with demo bills and surveys'

    def handle(self, *args, **options):
        self.stdout.write('Creating demo data...')
        
        # Clear existing demo data
        Bill.objects.filter(is_demo=True).delete()
        
        # Demo 1: Low-medium consumption household
        # 280 kWh, tarifa 1C, 4 personas, sin A/C, agua caliente gas
        demo1_bill = Bill.objects.create(
            tarifa='1C',
            periodo_inicio=date.today() - timedelta(days=60),
            periodo_fin=date.today(),
            consumo_kwh=280,
            total_recibo_mxn=None,
            is_demo=True
        )
        
        demo1_survey = Survey.objects.create(
            bill=demo1_bill,
            personas_en_casa=4,
            cuartos=4,
            ac_count=0,
            ac_horas_dia=0,
            refrigeradores=1,
            ref_antiguedad='mid',
            agua_caliente='gas',
            lavadora=True,
            secadora=False,
            home_office=True,
            bombeo_agua=False
        )
        
        # Calculate analysis for demo 1
        costo1 = compute_cost_mxn(demo1_bill.consumo_kwh, demo1_bill.tarifa)
        co2e1 = compute_co2e_kg(demo1_bill.consumo_kwh)
        calc1 = compute_breakdown_and_recs(demo1_bill, demo1_survey)
        
        AnalysisResult.objects.create(
            bill=demo1_bill,
            costo_estimado_mxn=costo1,
            co2e_kg=co2e1,
            breakdown_json=calc1['breakdown'],
            recomendaciones_json=calc1['recomendaciones'],
            supuestos_json=calc1['supuestos'],
            confianza_global=calc1['confianza_global']
        )
        
        self.stdout.write(self.style.SUCCESS(
            f'  ✓ Demo 1: {demo1_bill.consumo_kwh} kWh, Tarifa {demo1_bill.tarifa}, '
            f'Costo estimado: ${costo1}'
        ))
        
        # Demo 2: High consumption household (DAC)
        # 800 kWh, DAC, 3 personas, 2 A/C 6h/día, ref viejo, agua caliente eléctrica, secadora
        demo2_bill = Bill.objects.create(
            tarifa='DAC',
            periodo_inicio=date.today() - timedelta(days=60),
            periodo_fin=date.today(),
            consumo_kwh=800,
            total_recibo_mxn=None,
            is_demo=True
        )
        
        demo2_survey = Survey.objects.create(
            bill=demo2_bill,
            personas_en_casa=3,
            cuartos=5,
            ac_count=2,
            ac_horas_dia=6,
            refrigeradores=1,
            ref_antiguedad='old',
            agua_caliente='elec',
            lavadora=True,
            secadora=True,
            home_office=False,
            bombeo_agua=True
        )
        
        # Calculate analysis for demo 2
        costo2 = compute_cost_mxn(demo2_bill.consumo_kwh, demo2_bill.tarifa)
        co2e2 = compute_co2e_kg(demo2_bill.consumo_kwh)
        calc2 = compute_breakdown_and_recs(demo2_bill, demo2_survey)
        
        AnalysisResult.objects.create(
            bill=demo2_bill,
            costo_estimado_mxn=costo2,
            co2e_kg=co2e2,
            breakdown_json=calc2['breakdown'],
            recomendaciones_json=calc2['recomendaciones'],
            supuestos_json=calc2['supuestos'],
            confianza_global=calc2['confianza_global']
        )
        
        self.stdout.write(self.style.SUCCESS(
            f'  ✓ Demo 2: {demo2_bill.consumo_kwh} kWh, Tarifa {demo2_bill.tarifa}, '
            f'Costo estimado: ${costo2}'
        ))
        
        self.stdout.write(self.style.SUCCESS('\n✅ Demo data created successfully!'))
        self.stdout.write('   Visit http://localhost:8000 to see the demos.')
