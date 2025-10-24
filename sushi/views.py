from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.core.mail import send_mail
from django.contrib import messages
from django.utils import timezone
from django.db.models import Prefetch
import json

from .models import MenuCategory, MenuItem, SpecialMenu, Order, CustomUser, Contact, TableReservation
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
    # Use Categories as the primary source and prefetch their MenuItems ordered by name.
    # This guarantees each category block contains exactly the items saved under that category.
 
    categories = MenuCategory.objects.prefetch_related(
        Prefetch('menuitem_set', queryset=MenuItem.objects.order_by('name'))
    ).all()  # Remove order_by('name') to preserve database order of categories

    # Keep menuitems if other code expects it
    menuitems = MenuItem.objects.select_related('category').order_by('category__name', 'name').all()
    return render(request, 'menu.html', {'menuitems': menuitems, 'categories': categories})

def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')

        # Save to DB
        Contact.objects.create(name=name or 'Anonymous', email=email or '', message=message or '')

        subject = f'New message from {name}'
        full_message = f"From: {name} <{email}>\n\nMessage:\n{message}"

        try:
            send_mail(subject, full_message, email or None, ['saranvignesh55@gmail.com'])
            messages.success(request, 'Message sent successfully!')
        except Exception:
            messages.error(request, 'Failed to send message. Try again later.')

        return redirect('contact')

    return render(request, 'contact.html')

def table_reservation(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        date = request.POST.get('date')
        time = request.POST.get('time')
        guests = request.POST.get('guests') or 1
        special_requests = request.POST.get('special_requests', '')

        # Basic validation could be extended; here we save the reservation
        TableReservation.objects.create(
            name=name or 'Guest',
            email=email or '',
            phone=phone or '',
            date=date,
            time=time,
            guests=int(guests) if str(guests).isdigit() else 1,
            special_requests=special_requests
        )

        # optional: send confirmation email (best-effort)
        try:
            send_mail(
                'Reservation received',
                f'Thank you {name}, your reservation for {date} at {time} has been received.',
                'no-reply@example.com',
                [email] if email else []
            )
        except Exception:
            pass

        messages.success(request, 'Reservation submitted. We will contact you to confirm.')
        return redirect('table_reservation')

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

def menuitem_list(request):
    from collections import defaultdict
    from django.core.files.images import get_image_dimensions
    from django.core.exceptions import ValidationError
    menuitems = MenuItem.objects.select_related('category').all()
    menuitems_by_category = defaultdict(list)
    for item in menuitems:
        menuitems_by_category[item.category].append(item)
    categories = MenuCategory.objects.all()

    error_message = None

    if request.method == 'POST':
        form = MenuItemForm(request.POST, request.FILES)
        if 'image' in request.FILES:
            image_file = request.FILES['image']
            try:
                # Try to get image dimensions to validate image
                get_image_dimensions(image_file)
            except Exception:
                form.add_error('image', 'Upload a valid image. The file you uploaded was either not an image or a corrupted image.')
        if form.is_valid():
            form.save()
            return redirect('menuitem_list')
        else:
            # If image error, show error message
            if form.errors.get('image'):
                error_message = form.errors['image']
    else:
        form = MenuItemForm()

    return render(request, 'admin2/menuitem_list.html', {
        'menuitems_by_category': dict(menuitems_by_category),
        'categories': categories,
        'form': form,
        'error_message': error_message
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

def menuitem_delete(request, pk):
    item = get_object_or_404(MenuItem, pk=pk)
    if request.method == 'POST':
        item.delete()
        return redirect('menuitem_list')
    return render(request, 'admin2/menuitem_confirm_delete.html', {'item': item})

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
        # Accept both AJAX and regular POST
        category_name = request.POST.get('category_name') or request.POST.get('name')
        username = request.POST.get('username') or request.POST.get('added_by', 'admin')
        if category_name:
            MenuCategory.objects.create(name=category_name, added_by=username)
            # If AJAX, return JSON
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            # Otherwise, redirect back
            return redirect(request.META.get('HTTP_REFERER', '/'))
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Missing fields'})
        return redirect(request.META.get('HTTP_REFERER', '/'))
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'error': 'Invalid request'})
    return redirect(request.META.get('HTTP_REFERER', '/'))

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
    return render(request, 'admin2/menuitem_view.html', {'item': item})

def menuitem_add(request):
    if request.method == 'POST':
        form = MenuItemForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('menuitem_list')
    else:
        form = MenuItemForm()
    return render(request, 'admin2/menuitem_add.html', {'form': form})

def menuitem_update(request, pk):
    item = get_object_or_404(MenuItem, pk=pk)
    if request.method == 'POST':
        form = MenuItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            return redirect('menuitem_list')
    else:
        form = MenuItemForm(instance=item)
    return render(request, 'admin2/menuitem_add.html', {'form': form})

# ---------------- Order Processing ----------------

@csrf_exempt
def order_submit(request):
    # Accept both single-item payloads and a cart array from cart.html
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Please log in to place an order.'}, status=401)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # If cart array is provided, create an Order for each cart item
            cart = data.get('cart')
            if cart and isinstance(cart, list) and len(cart) > 0:
                # Basic validation: require mobile, address, delivery at top level
                mobile = data.get('mobile')
                address = data.get('address')
                delivery = data.get('delivery')
                order_type = data.get('orderType', 'now')
                order_date = data.get('orderDate') if order_type == 'later' else None
                order_time = data.get('orderTime') if order_type == 'later' else None

                if not all([mobile, address, delivery]):
                    return JsonResponse({'success': False, 'error': 'Missing required contact/delivery fields.'})

                created_ids = []
                for c in cart:
                    name = c.get('name') or c.get('item') or c.get('item_name')
                    price = c.get('price') or 0
                    qty = c.get('qty') or 1
                    if not name:
                        return JsonResponse({'success': False, 'error': 'Cart item missing name.'})
                    order = Order.objects.create(
                        item=name,
                        price=price,
                        qty=qty,
                        order_type=order_type,
                        order_date=order_date,
                        order_time=order_time,
                        email=request.user.email,
                        mobile=mobile,
                        address=address,
                        delivery=delivery,
                    )
                    created_ids.append(order.id)
                return JsonResponse({'success': True, 'order_ids': created_ids})
            else:
                # Fallback to single-item payload for compatibility
                required = ['item', 'price', 'qty', 'orderType', 'mobile', 'address', 'delivery']
                for field in required:
                    if not data.get(field):
                        return JsonResponse({'success': False, 'error': f'Missing {field}.'})
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

    pending_orders = Order.objects.filter(
        status__in=['pending', 'Accepted', 'Making', 'Ready to Collect']
    ).order_by('-created_at')
    
    orders_with_items = []
    for order in pending_orders:
        try:
            menu_item = MenuItem.objects.get(name=order.item)
            image = menu_item.image
        except MenuItem.DoesNotExist:
            image = None
        
        orders_with_items.append({
            'order': order,
            'image': image,
            'status_class': get_status_class(order.status),
            'created_at_formatted': order.created_at.strftime("%Y-%m-%d %H:%M:%S")
        })
    
    return render(request, 'admin2/order_live.html', {
        'orders_with_items': orders_with_items,
        'active_tab': 'live_orders'
    })

def get_status_class(status):
    status_classes = {
        'pending': 'bg-yellow-100 text-yellow-800',
        'Accepted': 'bg-blue-100 text-blue-800',
        'Making': 'bg-purple-100 text-purple-800',
        'Ready to Collect': 'bg-green-100 text-green-800',
        'Delivered': 'bg-gray-100 text-gray-800',
        'Cancelled': 'bg-red-100 text-red-800'
    }
    return status_classes.get(status, 'bg-gray-100 text-gray-800')

def order_food_table(request):
    if not request.user.is_staff:
        return redirect('admin_login')
        
    orders = Order.objects.exclude(
        status__in=['Delivered', 'Cancelled']
    ).order_by('-created_at')
    
    # Group orders by status for better organization
    orders_by_status = {
        'pending': orders.filter(status='pending'),
        'accepted': orders.filter(status='Accepted'),
        'making': orders.filter(status='Making'),
        'ready': orders.filter(status='Ready to Collect')
    }
    
    return render(request, 'admin2/order_food_table.html', {
        'orders_by_status': orders_by_status,
        'active_tab': 'food_orders'
    })

def manage_order_history(request):
    if not request.user.is_staff:
        return redirect('admin_login')

    # Add status filter
    status_filter = request.GET.get('status', '')
    date_filter = request.GET.get('date', '')
    
    orders = Order.objects.all()
    
    if status_filter:
        orders = orders.filter(status=status_filter)
    if date_filter:
        orders = orders.filter(created_at__date=date_filter)
        
    orders = orders.order_by('-created_at')
    
    # Get unique statuses for filter dropdown
    all_statuses = Order.objects.values_list('status', flat=True).distinct()
    
    return render(request, 'admin2/manage_order_history.html', {
        'orders': orders,
        'all_statuses': all_statuses,
        'current_status': status_filter,
        'current_date': date_filter,
        'active_tab': 'order_history'
    })

@login_required
def order_detail(request, pk):
    try:
        if request.user.is_staff:
            order = get_object_or_404(Order, pk=pk)
        else:
            order = get_object_or_404(Order, pk=pk, email=request.user.email)
            
        # Get associated menu item if exists
        try:
            menu_item = MenuItem.objects.get(name=order.item)
            item_image = menu_item.image
        except MenuItem.DoesNotExist:
            item_image = None
            
        context = {
            'order': order,
            'item_image': item_image,
            'status_class': get_status_class(order.status),
            'can_cancel': order.status in ['pending', 'Accepted'],
            'can_modify': request.user.is_staff,
            'active_tab': 'orders'
        }
        
        return render(request, 'order_detail.html', context)
        
    except Order.DoesNotExist:
        messages.error(request, 'Order not found.')
        return redirect('dashboard')

# Make this the main order_details view
order_details = order_detail

# ---------------- API Views ----------------

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.db.models import Q

@csrf_exempt
def search_menu_items_api(request):
    """
    Returns JSON list of menu items matching query.
    Each item includes: id, name, description, image_url, url (anchor to menu item id).
    """
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse([], safe=False)

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
            # Provide anchor that client can use to scroll: #menu-item-<id>
            'url': f'#menu-item-{item["id"]}'
        })
    return JsonResponse(results, safe=False)

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

@login_required
def admin_manage(request):
    """
    Management landing page for admin2 users.
    Ensures only staff or management users can access the admin manage page.
    """
    # Allow access for staff or management user_type
    if not request.user.is_authenticated or not (request.user.is_staff or getattr(request.user, "user_type", None) == "management"):
        return redirect('admin2_login')

    # Add any context metrics as needed later
    return render(request, 'admin2/adminmanage.html')


# sushi/views.py
from django.shortcuts import render

def order_card_list(request):
    return render(request, 'order_card_list.html')

def order_card_detail(request, pk):
    return render(request, 'order_card_detail.html')
    return render(request, 'order_card_detail.html', {'pk': pk})

def cart_page(request):
    return render(request, 'cart.html')

# ---------------- Admin Contact & Reservation Management ----------------

@login_required
def admin_contact_list(request):
    if not request.user.is_staff:
        return redirect('admin_login')
    
    contacts = Contact.objects.all().order_by('-created_at')
    return render(request, 'admin2/contact_list.html', {
        'contacts': contacts,
        'active_tab': 'contacts'
    })

@login_required
def admin_reservations(request):
    if not request.user.is_staff:
        return redirect('admin_login')
    
    # Filter options
    date_filter = request.GET.get('date')
    status_filter = request.GET.get('status')
    
    reservations = TableReservation.objects.all()
    if date_filter:
        reservations = reservations.filter(date=date_filter)
    if status_filter:
        reservations = reservations.filter(status=status_filter)
        
    reservations = reservations.order_by('date', 'time')
    
    return render(request, 'admin2/reservations.html', {
        'reservations': reservations,
        'active_tab': 'reservations'
    })

@login_required
def update_reservation_status(request, pk):
    if not request.user.is_staff:
        return redirect('admin_login')
        
    reservation = get_object_or_404(TableReservation, pk=pk)
    if request.method == 'POST':
        status = request.POST.get('status')
        if status in ['confirmed', 'cancelled']:
            reservation.status = status
            reservation.save()
            
            # Send email notification
            subject = f'Your table reservation for {reservation.date} has been {status}'
            message = f'Dear {reservation.name},\n\nYour table reservation for {reservation.date} at {reservation.time} has been {status}.'
            try:
                send_mail(subject, message, 'saranvignesh55@gmail.com', [reservation.email])
            except Exception as e:
                messages.error(request, f'Status updated but failed to send notification: {str(e)}')
                
    return redirect('admin_reservations')