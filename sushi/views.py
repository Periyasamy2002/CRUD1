from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.core.mail import send_mail
from django.contrib import messages
from django.utils import timezone
import json

from .models import MenuCategory, MenuItem, SpecialMenu, Order, CustomUser
from .forms import MenuItemForm, SpecialMenuForm
from django.db.models import Q

# ---------------- Public Views ----------------

def home(request):
    featured_menuitems = MenuItem.objects.filter(featured=True)[:6]
    special_menuitems = SpecialMenu.objects.all()[:6]
    return render(request, 'home.html', {
        'featured_menuitems': featured_menuitems,
        'special_menuitems': special_menuitems
    })

def menu(request):
    menuitems = MenuItem.objects.select_related('category').all()
    categories = MenuCategory.objects.all()
    return render(request, 'menu.html', {'menuitems': menuitems, 'categories': categories})

def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')

        subject = f'New message from {name}'
        full_message = f"From: {name} <{email}>\n\nMessage:\n{message}"

        try:
            send_mail(subject, full_message, email, ['saranvignesh55@gmail.com'])
            messages.success(request, 'Message sent successfully!')
        except:
            messages.error(request, 'Failed to send message. Try again later.')

        return redirect('contact')

    return render(request, 'contact.html')

def table_reservation(request):
    return render(request, 'reservation.html')

def order_menu(request):
    return render(request, 'order_menu.html')

# ---------------- Public Login & Signup ----------------

def login_view(request):
    if request.method == 'POST':
        identifier = request.POST.get('identifier')
        password = request.POST.get('password')
        user = None
        try:
            user_obj = CustomUser.objects.get(Q(username=identifier) | Q(email=identifier))
            user = authenticate(request, username=user_obj.username, password=password)
        except CustomUser.DoesNotExist:
            user = None
        if user is not None:
            auth_login(request, user)
            return redirect('dashboard')
        else:
            return render(request, 'login.html', {'login_error': 'Invalid username/email or password.'})
    return render(request, 'login.html')

def signup_view(request):
    # Customer signup (uses base.html)
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        if password != confirm_password:
            return render(request, 'login.html', {'signup_error': 'Passwords do not match'})
        if CustomUser.objects.filter(email=email).exists():
            return render(request, 'login.html', {'signup_error': 'Email already exists'})
        if CustomUser.objects.filter(username=username).exists():
            return render(request, 'login.html', {'signup_error': 'Username already exists'})
        user = CustomUser.objects.create_user(email=email, username=username, password=password)
        auth_login(request, user)
        return redirect('dashboard')
    return render(request, 'login.html')

def logout_view(request):
    auth_logout(request)
    return redirect('login')

@login_required
def dashboard(request):
    # Customer dashboard (uses base.html)
    return render(request, 'dashboard.html', {'user': request.user})

# ---------------- Admin Login ----------------

def admin_login(request):
    # Admin login (uses base2.html)
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('menuitem_list')

    error = None
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user is not None and user.is_staff:
            auth_login(request, user)
            return redirect('menuitem_list')
        else:
            error = "Invalid credentials or user does not have access."

    return render(request, "admin/login.html", {"error": error})

# ---------------- Admin2 Login ----------------

def admin2_login(request):
    if request.user.is_authenticated and getattr(request.user, "user_type", None) == "management":
        return redirect('admin2_dashboard')
    error = None
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        # Check user exists, is active, and is management type
        if user is not None and getattr(user, "user_type", None) == 'management' and user.is_active:
            auth_login(request, user)
            return redirect('admin2_dashboard')
        else:
            error = "Invalid username/password or not authorized."
    return render(request, "admin2/admin2_login.html", {"error": error})

def admin2_dashboard(request):
    if not request.user.is_authenticated or getattr(request.user, "user_type", None) != "management":
        return redirect('admin2_login')
    return render(request, 'admin2/admin2.html')

# ---------------- Admin Menu Management ----------------
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import MenuItem, MenuCategory

# ---------------- MenuItem Management ----------------

from collections import defaultdict

def menuitem_list(request):
    # Admin management page (uses base2.html)
    menuitems = MenuItem.objects.select_related('category').all()
    menuitems_by_category = defaultdict(list)
    for item in menuitems:
        menuitems_by_category[item.category].append(item)
    
    # Also pass the categories for the dropdown in the form
    categories = MenuCategory.objects.all()

    return render(request, 'admin2/menuitem_list.html', {
        'menuitems_by_category': dict(menuitems_by_category),
        'categories': categories
    })

def menuitem_create(request):
    categories = MenuCategory.objects.all()
    if request.method == 'POST':
        category_id = request.POST.get('category')
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        price = request.POST.get('price')
        image = request.FILES.get('image')
        try:
            category = MenuCategory.objects.get(id=category_id)
            MenuItem.objects.create(category=category, name=name, description=description, price=price, image=image)
            return redirect('menuitem_list')
        except MenuCategory.DoesNotExist:
            error_message = "Selected category does not exist."
            return render(request, 'admin/menuitem_form.html', {'categories': categories, 'error_message': error_message})
    return render(request, 'admin/menuitem_form.html', {'categories': categories})

def menuitem_edit(request, item_id):
    item = get_object_or_404(MenuItem, id=item_id)
    categories = MenuCategory.objects.all()
    if request.method == 'POST':
        item.name = request.POST.get('name')
        item.description = request.POST.get('description')
        item.price = request.POST.get('price')
        item.category = get_object_or_404(MenuCategory, id=request.POST.get('category'))
        if 'image' in request.FILES:
            item.image = request.FILES['image']
        item.save()
        return redirect('menuitem_list')
    return render(request, 'admin/menuitem_form.html', {'item': item, 'categories': categories})

def menuitem_delete(request, item_id):
    item = get_object_or_404(MenuItem, id=item_id)
    if request.method == 'POST':
        item.delete()
        return redirect('menuitem_list')
    return render(request, 'sushi/menuitem_confirm_delete.html', {'item': item})

# ---------------- Special Menu Management ----------------

@login_required
def special_menu(request, pk=None):
    if not request.user.is_staff:
        return redirect('admin_login')

    if pk:
        item = get_object_or_404(SpecialMenu, pk=pk)
    else:
        item = None

    if request.method == 'POST':
        form = SpecialMenuForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            return redirect('special_menu')
    else:
        form = SpecialMenuForm(instance=item)

    special_menu_items = SpecialMenu.objects.all()
    return render(request, 'admin2/special_menu.html', {
        'form': form,
        'item': item,
        'special_menu_items': special_menu_items
    })

@login_required
def special_menu_delete(request, pk):
    if not request.user.is_staff:
        return redirect('admin_login')
    item = get_object_or_404(SpecialMenu, pk=pk)
    item.delete()
    return redirect('special_menu')

@login_required
def special_menu_update(request, pk):
    if not request.user.is_staff:
        return redirect('admin_login')
    item = get_object_or_404(SpecialMenu, pk=pk)
    if request.method == 'POST':
        form = SpecialMenuForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            return redirect('special_menu')
    else:
        form = SpecialMenuForm(instance=item)
    special_menu_items = SpecialMenu.objects.all()
    return render(request, 'admin2/special_menu.html', {
        'form': form,
        'item': item,
        'special_menu_items': special_menu_items
    })

# ---------------- Category Management ----------------

@csrf_exempt
def category_create(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        added_by = request.POST.get('added_by', 'admin')
        if name:
            MenuCategory.objects.create(name=name, added_by=added_by)
            return JsonResponse({'success': True})
        return JsonResponse({'success': False, 'error': 'Missing fields'})
    return JsonResponse({'success': False, 'error': 'Invalid request'})

def category_edit(request, pk):
    category = get_object_or_404(MenuCategory, pk=pk)
    if request.method == 'POST':
        category.name = request.POST.get('name')
        category.added_by = request.POST.get('added_by', 'admin')
        category.save()
        return redirect('menuitem_list')
    return render(request, 'menu_management.html', {'category': category})

def category_delete(request, pk):
    category = get_object_or_404(MenuCategory, pk=pk)
    category.delete()
    return redirect('menuitem_list')
# ---------------- Menu Item Details / Add / Update ----------------

def menuitem_view(request, pk):
    item = get_object_or_404(MenuItem, pk=pk)
    return render(request, 'menuitem_view.html', {'item': item})

def menuitem_add(request):
    if request.method == 'POST':
        form = MenuItemForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('menuitem_list')
    else:
        form = MenuItemForm()
    return render(request, 'menuitem_add.html', {'form': form})

def menuitem_update(request, pk):
    item = get_object_or_404(MenuItem, pk=pk)
    if request.method == 'POST':
        form = MenuItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            return redirect('menuitem_list')
    else:
        form = MenuItemForm(instance=item)
    return render(request, 'menuitem_add.html', {'form': form})

# ---------------- Order Processing ----------------

@csrf_exempt
def order_submit(request):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Please log in to place an order.'}, status=401)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            required = ['item', 'price', 'qty', 'orderType', 'mobile', 'address', 'delivery']
            for field in required:
                if not data.get(field):
                    return JsonResponse({'success': False, 'error': f'Missing {field}.'})
            if data['orderType'] == 'later' and (not data.get('orderDate') or not data.get('orderTime')):
                return JsonResponse({'success': False, 'error': 'Date and time required for scheduled order.'})
            order = Order.objects.create(
                item=data['item'],
                price=data['price'],
                qty=data['qty'],
                order_type=data['orderType'],
                order_date=data.get('orderDate') or None,
                order_time=data.get('orderTime') or None,
                email=request.user.email,
                mobile=data['mobile'],
                address=data['address'],
                delivery=data['delivery'],
            )
            return JsonResponse({'success': True, 'order_id': order.id})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@login_required
def order_action(request, order_id):
    order = get_object_or_404(Order, id=order_id, email=request.user.email)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'get':
            order.status = 'got'
        elif action == 'out':
            order.status = 'out'
        elif action == 'cancel':
            order.status = 'cancelled'
        order.save()
    return redirect('order_details')

@login_required
def order_action_admin(request, order_id):
    if not request.user.is_staff and getattr(request.user, "user_type", None) != "management":
        return redirect('admin2_login')
    order = get_object_or_404(Order, id=order_id)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'accept':
            order.status = 'Accepted'
            order.save()
        elif action == 'making':
            order.status = 'Making'
            order.save()
        elif action == 'collect':
            order.status = 'Ready to Collect'
            order.save()
        elif action == 'delivered':
            order.status = 'Delivered'
            order.save()
        elif action == 'cancel':
            order.status = 'Cancelled'
            order.save()
            return redirect('order_food_table')
    return redirect('order_food_table')

@login_required
def order_history(request):
    orders = Order.objects.filter(email=request.user.email).order_by('-created_at')
    return render(request, 'order_history.html', {'orders': orders})

@login_required
def order_detail(request, pk):
    order = Order.objects.get(pk=pk, email=request.user.email)
    return render(request, 'order_detail.html', {'order': order})

# Alias for URL compatibility
order_details = order_detail

@login_required
def order_live_track(request):
    orders = Order.objects.filter(email=request.user.email, status='pending').order_by('-created_at')
    return render(request, 'order_live_track.html', {'orders': orders})

@login_required
def order_track(request, pk):
    order = Order.objects.get(pk=pk, email=request.user.email)
    return render(request, 'order_track.html', {'order': order})

@login_required
def order_live(request):
    if not request.user.is_staff:
        return redirect('admin_login')

    pending_orders = Order.objects.filter(status='pending').order_by('created_at')
    
    orders_with_items = []
    for order in pending_orders:
        try:
            menu_item = MenuItem.objects.get(name=order.item)
            image = menu_item.image
        except MenuItem.DoesNotExist:
            image = None
        
        orders_with_items.append({
            'order': order,
            'image': image
        })

def order_food_table(request):
    orders = Order.objects.exclude(status__in=['Delivered', 'Canceled']).order_by('created_at')
    return render(request, 'admin2/order_food_table.html', {'orders': orders})

def manage_order_history(request):
    orders = Order.objects.all().order_by('-created_at')
    return render(request, 'admin2/manage_order_history.html', {'orders': orders})

# ---------------- API Views ----------------

@csrf_exempt
def search_menu_items_api(request):
    query = request.GET.get('q', '')
    if query:
        menu_items = MenuItem.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        ).values('id', 'name', 'description', 'image')
        
        results = []
        for item in menu_items:
            image_url = item['image'].url if item['image'] else None
            results.append({
                'id': item['id'],
                'name': item['name'],
                'description': item['description'],
                'image_url': image_url,
                'url': f'#menu-item-{item['id']}' # Anchor link to the item
            })
        return JsonResponse(results, safe=False)
    return JsonResponse([], safe=False)

def admin_manage(request):
    # You can customize the context or template as needed
    return render(request, 'admin2/adminmanage.html')

@login_required
def delete_order(request, pk):
    if not request.user.is_staff:
        return redirect('admin_login')
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        order.delete()
        return redirect('order_live')
    return render(request, 'order_confirm_delete.html', {'order': order})
@login_required
def update_order_status(request, pk):
    if not request.user.is_staff:
        return redirect('admin_login')

    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        status = request.POST.get('status')
        if status:
            order.status = status
            order.save()

            # Send email notification
            subject = f'Your order #{order.id} has been {status}'
            message = f'Hi, your order for {order.item} has been {status}.'
            try:
                send_mail(subject, message, 'saranvignesh55@gmail.com', [order.email])
                messages.success(request, f'Order #{order.id} updated to {status} and notification sent.')
            except Exception as e:
                messages.error(request, f'Order status updated, but failed to send notification. Error: {e}')

    return redirect('manage_order_history')

# ---------------- API Views ----------------

@csrf_exempt
def search_menu_items_api(request):
    query = request.GET.get('q', '')
    if query:
        menu_items = MenuItem.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        ).values('id', 'name', 'description', 'image')
        
        results = []
        for item in menu_items:
            image_url = item['image'].url if item['image'] else None
            results.append({
                'id': item['id'],
                'name': item['name'],
                'description': item['description'],
                'image_url': image_url,
                'url': f'#menu-item-{item['id']}' # Anchor link to the item
            })
        return JsonResponse(results, safe=False)
    return JsonResponse([], safe=False)



@login_required
def delete_order(request, pk):
    if not request.user.is_staff:
        return redirect('admin_login')
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        order.delete()
        return redirect('order_live')
    return render(request, 'order_confirm_delete.html', {'order': order})

@login_required
def order_card_list(request):
    # Show all orders for the logged-in user as cards
    orders = Order.objects.filter(email=request.user.email).order_by('-created_at')
    return render(request, 'order_card_list.html', {'orders': orders})

@login_required
def order_card_detail(request, pk):
    # Show details and live status/actions for a single order
    order = get_object_or_404(Order, pk=pk, email=request.user.email)
    steps = [
        "Accepted",
        "Making",
        "Ready to Collect",
        "Delivered",
        "Cancelled"
    ]
    # Find the index of the current status in steps, default to 0 if not found
    try:
        current_step_index = steps.index(order.status)
    except ValueError:
        current_step_index = 0
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status and new_status in steps:
            order.status = new_status
            order.save()
            current_step_index = steps.index(order.status)
    return render(request, 'order_card_detail.html', {'order': order, 'steps': steps, 'current_step_index': current_step_index})