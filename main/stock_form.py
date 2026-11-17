from django import forms
from .models import StockPart
 
class StockPartForm(forms.ModelForm):
 
    class Meta:
        model = StockPart
 
        fields = [
            'name',
            'category',
            'quantity',
            'min_quantity',
            'price',
            'supplier',
            'description',
        ]
 
        labels = {
            'name': 'Название запчасти',
            'category': 'Категория',
            'quantity': 'Количество на складе',
            'min_quantity': 'Минимальный остаток',
            'price': 'Цена за единицу',
            'supplier': 'Поставщик',
            'description': 'Описание',
        }
 
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Например, экран для смартфона'
            }),
 
            'category': forms.TextInput(attrs={
                'placeholder': 'Например, Экраны'
            }),
 
            'quantity': forms.NumberInput(attrs={
                'min': 0
            }),
 
            'min_quantity': forms.NumberInput(attrs={
                'min': 0
            }),
 
            'price': forms.NumberInput(attrs={
                'min': 0,
                'step': '0.01'
            }),
 
            'supplier': forms.TextInput(attrs={
                'placeholder': 'Название поставщика'
            }),
 
            'description': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Дополнительная информация'
            }),
        }
 
 