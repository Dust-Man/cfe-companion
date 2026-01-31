"""
URL configuration for the Energy app.
"""

from django.urls import path
from . import views

app_name = 'energy'

urlpatterns = [
    # Home
    path('', views.home, name='home'),
    
    # Wizard
    path('new/', views.new_bill, name='new_bill'),
    path('bill/', views.create_bill, name='create_bill'),
    path('survey/<int:bill_id>/', views.survey, name='survey'),
    path('results/<int:bill_id>/', views.results, name='results'),
    
    # Demo
    path('demo/<int:demo_id>/', views.load_demo, name='load_demo'),
    
    # Historial (opcional)
    path('history/', views.history, name='history'),
]
