"""
Tests for the Electric Assistant MVP.
"""

from decimal import Decimal
from django.test import TestCase
from .services.calculations import compute_cost_mxn, compute_co2e_kg


class CostCalculationTests(TestCase):
    """Tests for compute_cost_mxn function."""
    
    def test_basic_consumption(self):
        """Test cost for basic consumption (< 150 kWh)."""
        # 100 kWh at basic rate: 100 * 0.98 * 1.16 = 113.68
        cost = compute_cost_mxn(100, '1C')
        self.assertAlmostEqual(float(cost), 113.68, places=0)
    
    def test_intermediate_consumption(self):
        """Test cost for intermediate consumption (150-280 kWh)."""
        # 200 kWh: 150*0.98 + 50*1.19 = 147 + 59.5 = 206.5 * 1.16 = 239.54
        cost = compute_cost_mxn(200, '1C')
        self.assertAlmostEqual(float(cost), 239.54, places=0)
    
    def test_excedent_consumption(self):
        """Test cost for excedent consumption (280-500 kWh)."""
        # 350 kWh: 150*0.98 + 130*1.19 + 70*3.52 = 147 + 154.7 + 246.4 = 548.1 * 1.16 = 635.80
        cost = compute_cost_mxn(350, '1C')
        self.assertAlmostEqual(float(cost), 635.80, places=0)
    
    def test_dac_tariff(self):
        """Test cost for DAC tariff (high rate)."""
        # 300 kWh at DAC: 300 * 6.38 * 1.16 = 2220.24
        cost = compute_cost_mxn(300, 'DAC')
        self.assertAlmostEqual(float(cost), 2220.24, places=0)
    
    def test_high_consumption_becomes_dac(self):
        """Test that consumption > 500 kWh uses DAC rate."""
        # 600 kWh: should use DAC rate regardless of declared tariff
        cost = compute_cost_mxn(600, '1C')
        expected = 600 * 6.38 * 1.16  # 4440.48
        self.assertAlmostEqual(float(cost), expected, places=0)


class CO2CalculationTests(TestCase):
    """Tests for compute_co2e_kg function."""
    
    def test_co2e_calculation(self):
        """Test CO2e calculation with standard factor."""
        # 100 kWh * 0.444 = 44.4 kg CO2e
        co2e = compute_co2e_kg(100)
        self.assertEqual(co2e, Decimal('44.40'))
    
    def test_co2e_zero(self):
        """Test CO2e for zero consumption."""
        co2e = compute_co2e_kg(0)
        self.assertEqual(co2e, Decimal('0.00'))
    
    def test_co2e_high_consumption(self):
        """Test CO2e for high consumption."""
        # 1000 kWh * 0.444 = 444 kg CO2e
        co2e = compute_co2e_kg(1000)
        self.assertEqual(co2e, Decimal('444.00'))
