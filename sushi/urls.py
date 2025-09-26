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
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),
    path('adminmanage/', views.admin_manage, name='admin_manage'),

    # ----------- Admin Routes -----------
    path('admin2/', views.admin2_login, name='admin2_login'),
    path('admin2/dashboard/', views.admin2_dashboard, name='admin2_dashboard'),
    path('dashboard/login/', views.admin_login, name='admin_login'),

    # --- Menu Items ---
    path('menuitems/', views.menuitem_list, name='menuitem_list'),       # List all
    path('menuitems/add/', views.menuitem_add, name='menuitem_add'),     # Add new
    path('menuitems/<int:pk>/view/', views.menuitem_view, name='menuitem_view'),
    path('menuitems/<int:pk>/edit/', views.menuitem_edit, name='menuitem_edit'),
    path('menuitems/<int:pk>/update/', views.menuitem_update, name='menuitem_update'),
    path('menuitems/<int:pk>/delete/', views.menuitem_delete, name='menuitem_delete'),

    # --- Categories ---
    path('category/create/', views.category_create, name='category_create'),
    path('category/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('category/<int:pk>/delete/', views.category_delete, name='category_delete'),

    # --- Special Menu ---
    path('special_menu/', views.special_menu, name='special_menu'),
    path('special_menu/update/<int:pk>/', views.special_menu, name='special_menu_update'),
    path('special_menu/delete/<int:pk>/', views.special_menu_delete, name='special_menu_delete'),

    # --- Orders ---
    path('order/manage_history/', views.manage_order_history, name='manage_order_history'),
    path('order/food_table/', views.order_food_table, name='order_food_table'),
    path('order/history/', views.order_history, name='order_history'),
    path('order/delete/<int:pk>/', views.delete_order, name='delete_order'),
    path('order/live/', views.order_live, name='order_live'),
    path('order/update_status/<int:pk>/<str:status>/', views.update_order_status, name='update_order_status'),
    path('order/live-track/', views.order_live_track, name='order_live_track'),
    path('order/details/', views.order_details, name='order_details'),
    path('order/submit/', views.order_submit, name='order_submit'),
    path('order/<int:order_id>/action/', views.order_action, name='order_action'),

    # --- API ---
    path('api/search_menu_items/', views.search_menu_items_api, name='search_menu_items_api'),

    # --- Dashboard ---
    path('dashboard/', views.dashboard, name='dashboard'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)