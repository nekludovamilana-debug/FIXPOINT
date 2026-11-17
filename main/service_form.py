from django import forms
from .models import Service
 
class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
 
        fields = [
            'name',
            'category',
            'description',
            'price',
            'duration',
            'is_active',
        ]
 
        labels = {
            'name': 'Название услуги',
            'category': 'Категория',
            'description': 'Описание',
            'price': 'Стоимость',
            'duration': 'Продолжительность',
            'is_active': 'Показывать на сайте',
        }
 
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Например, Диагностика компьютера'
            }),
 
            'description': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Описание услуги'
            }),
 
            'price': forms.NumberInput(attrs={
                'min': '0',
                'step': '0.01'
            }),
 
            'duration': forms.TextInput(attrs={
                'placeholder': 'Например, 1–2 часа'
            }),
        }
 