from django.contrib import admin
from .models import MenuCategory, MenuItem, SpecialMenu

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'featured')
    list_filter = ('category', 'featured')
    search_fields = ('name',)

@admin.register(SpecialMenu)
class SpecialMenuAdmin(admin.ModelAdmin):
    list_display = ('title', 'subtitle', 'price')
    search_fields = ('title', 'subtitle')

admin.site.register(MenuCategory)
