from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

User = get_user_model()

class EmployeeCreationForm(UserCreationForm):
    email = forms.EmailField(required=False, label='Электронная почта')
    first_name = forms.CharField(max_length=150, required=False, label='Имя')
    last_name = forms.CharField(max_length=150, required=False, label='Фамилия')
    is_superuser = forms.BooleanField(required=False, label='Права администратора')

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2', 'is_superuser')
        labels = {'username': 'Логин'}

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data.get('email', '')
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        user.is_staff = True
        user.is_superuser = self.cleaned_data.get('is_superuser', False)
        if commit:
            user.save()
        return user
