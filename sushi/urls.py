from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # ----------- Public Routes -----------
    path('', views.home, name='home'),
    path('menu/', views.menu, name='menu'),
    path('contact/', views.contact, name='contact'),
    path('reservation/', views.table_reservation, name='reservation'),
    path('order/', views.order_menu, name='order_menu'),
    path('login/', views.login_view, name='login'),

    # ----------- Admin Routes -----------
    path('dashboard/login/', views.admin_login, name='admin_login'),
    path('menuitems/', views.menuitem_list, name='menuitem_list'),
    path('dashboard/menuitems/create/', views.menuitem_create, name='menuitem_create'),
    path('dashboard/menuitems/edit/<int:item_id>/', views.menuitem_edit, name='menuitem_edit'),
    path('dashboard/menuitems/delete/<int:item_id>/', views.menuitem_delete, name='menuitem_delete'),
    path('category/create/', views.category_create, name='category_create'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)