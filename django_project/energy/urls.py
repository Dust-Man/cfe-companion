"""
URL configuration for the Energy app.
"""

from django.urls import path
from . import views
from .views_ocr import extract_bill

app_name = 'energy'

urlpatterns = [
    # Home
    path('', views.home, name='home'),

    # Wizard
    path('new/', views.new_bill, name='new_bill'),
    path('bill/', views.create_bill, name='create_bill'),
    path('survey/<int:bill_id>/', views.survey, name='survey'),
    path('results/<int:bill_id>/', views.results, name='results'),
    path('dashboard/<int:bill_id>/', views.dashboard, name='dashboard'),

    # OCR
    path('extract-bill/', extract_bill, name='extract_bill'),

    # Demo
    path('demo/<int:demo_id>/', views.load_demo, name='load_demo'),

    # Historial
    path('history/', views.history, name='history'),
]