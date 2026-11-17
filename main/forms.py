from django import forms
from django.contrib.auth import get_user_model
from .models import RepairRequest, Service, RepairComment, StockPart

User = get_user_model()


class RepairRequestForm(forms.ModelForm):
    service = forms.ModelChoiceField(
        queryset=Service.objects.filter(is_active=True),
        label='Выберите услугу',
        empty_label='Выберите услугу из списка',
        required=True
    )

    class Meta:
        model = RepairRequest
        fields = ['customer_name', 'phone', 'device', 'service', 'problem', 'photo']
        labels = {
            'customer_name': 'Ваше имя',
            'phone': 'Номер телефона',
            'device': 'Ваше устройство',
            'problem': 'Описание неисправности',
            'photo': 'Фотография неисправности',
        }
        widgets = {
            'customer_name': forms.TextInput(attrs={'placeholder': 'Введите ваше имя'}),
            'phone': forms.TextInput(attrs={'placeholder': '+7 (999) 123-45-67'}),
            'device': forms.TextInput(attrs={'placeholder': 'Например, ноутбук ASUS'}),
            'problem': forms.Textarea(attrs={'placeholder': 'Опишите неисправность', 'rows': 4}),
            'photo': forms.ClearableFileInput(attrs={'accept': 'image/jpeg,image/png,image/webp'}),
        }

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if not photo:
            return photo
        if photo.size > 5 * 1024 * 1024:
            raise forms.ValidationError('Размер фотографии не должен превышать 5 МБ.')
        content_type = getattr(photo, 'content_type', '')
        if content_type not in ('image/jpeg', 'image/png', 'image/webp'):
            raise forms.ValidationError('Разрешены только JPG, PNG и WEBP.')
        # Проверяем реальное содержимое изображения, а не только расширение/MIME.
        try:
            from PIL import Image
            image = Image.open(photo)
            image.verify()
            if image.format not in ('JPEG', 'PNG', 'WEBP'):
                raise forms.ValidationError('Файл не является допустимым изображением.')
            photo.seek(0)
        except forms.ValidationError:
            raise
        except Exception:
            raise forms.ValidationError('Не удалось прочитать изображение. Выберите другой файл.')
        return photo


class RepairCommentForm(forms.ModelForm):
    text = forms.CharField(max_length=5000, label='Комментарий', widget=forms.Textarea(attrs={'rows': 3, 'maxlength': 5000, 'placeholder': 'Напишите комментарий к заявке'}))

    class Meta:
        model = RepairComment
        fields = ['text']
        labels = {'text': 'Комментарий'}
        widgets = {
            'text': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Напишите комментарий к заявке',
                'maxlength': 5000,
            })
        }


class RepairPartUsageForm(forms.Form):
    part = forms.ModelChoiceField(
        queryset=StockPart.objects.order_by('name'),
        label='Запчасть'
    )
    quantity = forms.IntegerField(
        min_value=1,
        label='Количество',
        widget=forms.NumberInput(attrs={'min': 1})
    )


class RepairLaborCostForm(forms.Form):
    labor_cost = forms.DecimalField(
        min_value=0, max_digits=10, decimal_places=2, label='Стоимость работ (₽)',
        widget=forms.NumberInput(attrs={'min': '0', 'step': '0.01'})
    )
