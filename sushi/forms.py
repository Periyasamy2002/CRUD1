from django import forms
from .models import MenuItem, SpecialMenu

class MenuItemForm(forms.ModelForm):
    class Meta:
        model = MenuItem
        fields = ['category', 'name', 'description', 'price', 'image', 'featured']

class SpecialMenuForm(forms.ModelForm):
    class Meta:
        model = SpecialMenu
        fields = ['image', 'title', 'subtitle', 'price']
