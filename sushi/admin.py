from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, MenuCategory, MenuItem, SpecialMenu, Order, Contact, TableReservation

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('username', 'email', 'user_type', 'is_staff', 'is_active')
    list_filter = ('user_type', 'is_staff', 'is_active')
    search_fields = ('username', 'email')
    ordering = ('username',)
    readonly_fields = ('date_joined',)  # Make date_joined read-only
    fieldsets = (
        (None, {'fields': ('username', 'email', 'password', 'user_type')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),  # date_joined is read-only
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'user_type', 'password1', 'password2'),
        }),
    )

admin.site.register(CustomUser, CustomUserAdmin)

@admin.register(MenuCategory)
class MenuCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'added_by')
    search_fields = ('name',)

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'featured')
    list_filter = ('category', 'featured')
    search_fields = ('name',)

@admin.register(SpecialMenu)
class SpecialMenuAdmin(admin.ModelAdmin):
    list_display = ('title', 'subtitle', 'price')
    search_fields = ('title', 'subtitle')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('item', 'qty', 'price', 'order_type', 'email', 'status', 'created_at')
    list_filter = ('order_type', 'status', 'created_at')
    search_fields = ('item', 'email')

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'created_at', 'status')
    list_filter = ('status', 'created_at')
    search_fields = ('name', 'email', 'message')

@admin.register(TableReservation)
class TableReservationAdmin(admin.ModelAdmin):
    list_display = ('name', 'date', 'time', 'guests', 'status', 'created_at')
    list_filter = ('status', 'date')
    search_fields = ('name', 'email', 'phone')