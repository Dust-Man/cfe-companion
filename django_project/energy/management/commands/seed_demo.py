"""
Command to seed demo data for the Electric Assistant MVP.
Creates two example bills with surveys (new JSONField format).
"""

from datetime import date, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from energy.models import Bill, Survey, AnalysisResult
from energy.services.calculations import compute_cost_mxn, compute_co2e_kg


class Command(BaseCommand):
    help = 'Seeds the database with demo bills and surveys'

    def handle(self, *args, **options):
        self.stdout.write('Creating demo data...')
        
        # Clear existing demo data
        Bill.objects.filter(is_demo=True).delete()
        
        # ──────────────────────────────────────────────────────────────
        # Demo 1: consumo medio, sin A/C, agua caliente por gas
        # ──────────────────────────────────────────────────────────────
        demo1_bill = Bill.objects.create(
            tarifa='1C',
            periodo_inicio=date.today() - timedelta(days=60),
            periodo_fin=date.today(),
            consumo_kwh=280,
            total_recibo_mxn=Decimal('245.00'),
            periodo_basico_kwh=150,
            periodo_intermedio_kwh=130,
            periodo_excedente_kwh=0,
            subtotal_basico_mxn=Decimal('147.00'),
            subtotal_intermedio_mxn=Decimal('154.70'),
            subtotal_excedente_mxn=Decimal('0.00'),
            subsidio_mxn=Decimal('25.00'),
            is_demo=True
        )
        
        Survey.objects.create(
            bill=demo1_bill,
            respuestas={
                "cambios_recientes": ["mas_tiempo_casa"],
                "tiene_ac": "no",
                "agua_caliente_tipo": "gas",
                "refrigeradores": "1",
                "ref_antiguedad": "medio",
                "tiene_secadora": "no",
                "tiene_bomba": "no",
                "tiene_bomba_alberca": "no",
                "calefactor": "no",
                "cocina_tipo": "gas",
                "cocina_horno": "no",
                "cocina_airfryer": "no",
                "cocina_parrilla": "no",
                "cocina_hervidor": "diario",
                "tvs": "1",
                "pc_uso": "4-8",
                "consola": "no",
                "siempre_encendidos": ["router"],
                "culpables_ocultos": ["dispensador_agua"],
                "culpables_uso": "1-2",
            }
        )
        
        self.stdout.write(self.style.SUCCESS(
            f'  ✓ Demo 1: {demo1_bill.consumo_kwh} kWh, Tarifa {demo1_bill.tarifa}'
        ))
        
        # ──────────────────────────────────────────────────────────────
        # Demo 2: alto consumo, DAC, 2 A/C, agua eléctrica, secadora
        # ──────────────────────────────────────────────────────────────
        demo2_bill = Bill.objects.create(
            tarifa='DAC',
            periodo_inicio=date.today() - timedelta(days=60),
            periodo_fin=date.today(),
            consumo_kwh=800,
            total_recibo_mxn=Decimal('3200.00'),
            periodo_basico_kwh=150,
            periodo_intermedio_kwh=130,
            periodo_excedente_kwh=520,
            subtotal_basico_mxn=Decimal('147.00'),
            subtotal_intermedio_mxn=Decimal('154.70'),
            subtotal_excedente_mxn=Decimal('1824.00'),
            subsidio_mxn=Decimal('0.00'),
            is_demo=True
        )
        
        Survey.objects.create(
            bill=demo2_bill,
            respuestas={
                "cambios_recientes": ["ola_calor", "aparato_nuevo"],
                "tiene_ac": "minisplit_no_inverter",
                "ac_unidades": "2",
                "ac_dias_semana": "7",
                "ac_horas_dia": "6-8",
                "ac_temperatura": "21-23",
                "agua_caliente_tipo": "electrico",
                "agua_caliente_equipo": ["boiler_electrico"],
                "agua_personas": "3-4",
                "agua_duracion": "11-15",
                "refrigeradores": "2",
                "ref_antiguedad": "viejo",
                "tiene_secadora": "electrica",
                "secadora_cargas": "3-4",
                "secadora_alto_calor": "si",
                "tiene_bomba": "si",
                "bomba_frecuencia": "mucho",
                "tiene_bomba_alberca": "si",
                "bomba_alberca_horas": "6+",
                "calefactor": "no",
                "cocina_tipo": "mixta",
                "cocina_horno": "1-2",
                "cocina_airfryer": "4+",
                "cocina_parrilla": "poco",
                "cocina_hervidor": "diario",
                "tvs": "2",
                "pc_uso": "9+",
                "consola": "4+",
                "siempre_encendidos": ["router", "camaras", "servidor"],
                "culpables_ocultos": ["lavavajillas", "deshumidificador", "enfriador_aire"],
                "culpables_uso": "3-5",
            }
        )
        
        self.stdout.write(self.style.SUCCESS(
            f'  ✓ Demo 2: {demo2_bill.consumo_kwh} kWh, Tarifa {demo2_bill.tarifa}'
        ))
        
        self.stdout.write(self.style.SUCCESS('\n✅ Demo data created successfully!'))
        self.stdout.write('   Visit http://localhost:8000 to see the demos.')