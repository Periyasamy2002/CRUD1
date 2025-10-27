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
from django.urls import reverse
from django.conf import settings
import logging

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
        name = (request.POST.get('name') or '').strip()
        email = (request.POST.get('email') or '').strip()
        message = (request.POST.get('message') or '').strip()

        # Basic validation
        if not email:
            messages.error(request, 'Please provide a valid email address.')
            return redirect('contact')

        # Save to DB (safe guard)
        try:
            Contact.objects.create(name=name or 'Anonymous', email=email, message=message)
        except Exception as e:
            logging.exception("Failed to save contact message")
            messages.error(request, 'Failed to save your message. Please try again later.')
            return redirect('contact')

        subject = f'New message from {name or "Anonymous"}'
        full_message = f"From: {name} <{email}>\n\nMessage:\n{message}"

        # Use configured DEFAULT_FROM_EMAIL as sender, and notify site owner(s)
        try:
            send_mail(subject, full_message, settings.DEFAULT_FROM_EMAIL, [settings.EMAIL_HOST_USER])
            messages.success(request, 'Message sent successfully!')
        except Exception as e:
            logging.exception("Failed to send contact notification email")
            # Still treat as saved; inform user that email failed
            messages.success(request, 'Message saved. Notification email could not be sent at this time.')

        return redirect('contact')

    return render(request, 'contact.html')

def table_reservation(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        # Ensure phone is never None (prevent DB NOT NULL errors)
        phone = request.POST.get('phone') or ''
        date = request.POST.get('date')
        time = request.POST.get('time')
        # accept either 'guests' or legacy 'people' field
        guests = request.POST.get('guests') or request.POST.get('people') or 1
        special_requests = request.POST.get('special_requests', '')

        # Basic validation could be extended; here we save the reservation
        TableReservation.objects.create(
            name=name or 'Guest',
            email=email or '',
            phone=phone,
            date=date,
            time=time,
            guests=int(guests) if str(guests).isdigit() else 1,
            special_requests=special_requests
        )

        # optional: send confirmation email (best-effort) only if email provided
        if email:
            try:
                send_mail(
                    'Reservation received',
                    f'Thank you {name}, your reservation for {date} at {time} has been received.',
                    'no-reply@example.com',
                    [email]
                )
            except Exception:
                pass

        messages.success(request, 'Reservation submitted. We will contact you to confirm.')
        # Redirect to the correct URL name and include success flag for template
        return redirect(reverse('reservation') + '?success=1')

    # On GET, show reservation_success if query param present
    reservation_success = request.GET.get('success') == '1'
    return render(request, 'reservation.html', {'reservation_success': reservation_success})

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
    """
    Accepts both JSON (AJAX) and regular form POSTs.
    Supports:
      - cart: [ {name, price, qty}, ... ]  (JSON array)
      - single item: item, price, qty, mobile, address, delivery, orderType
    For guest users, an 'email' field is required.
    On success:
      - For JSON requests: returns JsonResponse with created order ids
      - For form POSTs: stores created ids in session['last_order_ids'] and redirects to cart_page
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

    # Determine request type (JSON/AJAX vs form)
    is_json = request.content_type == 'application/json' or request.headers.get('x-requested-with') == 'XMLHttpRequest'

    try:
        # Parse payload
        if is_json:
            try:
                data = json.loads(request.body.decode('utf-8') or '{}')
            except Exception:
                return JsonResponse({'success': False, 'error': 'Invalid JSON payload'}, status=400)
        else:
            # POST form; attempt to read a JSON 'cart' field if present
            data = request.POST.dict()
            if 'cart' in request.POST:
                try:
                    data['cart'] = json.loads(request.POST['cart'])
                except Exception:
                    data['cart'] = None

        # Determine email (guest must provide, logged-in users may omit)
        email = data.get('email') or (request.user.email if getattr(request, 'user', None) and request.user.is_authenticated else None)
        if not email:
            if is_json:
                return JsonResponse({'success': False, 'error': 'Email is required for guest orders.'}, status=400)
            messages.error(request, 'Email is required to place an order.')
            return redirect('cart_page')

        created_ids = []
        cart = data.get('cart')
        # Normalize some possible field names
        def _num(v, default=0):
            try:
                return float(v)
            except Exception:
                return default

        if cart and isinstance(cart, list):
            # Bulk/cart create
            mobile = data.get('mobile') or data.get('phone') or ''
            address = data.get('address') or ''
            delivery = data.get('delivery') or ''
            order_type = data.get('orderType') or data.get('order_type') or 'now'
            order_date = data.get('orderDate') if order_type == 'later' else None
            order_time = data.get('orderTime') if order_type == 'later' else None

            # Simple contact validation for cart orders
            if not (mobile and address and delivery):
                if is_json:
                    return JsonResponse({'success': False, 'error': 'Missing contact/delivery info for cart order.'}, status=400)
                messages.error(request, 'Please provide phone, address and delivery option.')
                return redirect('cart_page')

            for c in cart:
                name = c.get('name') or c.get('item') or c.get('item_name')
                price = _num(c.get('price'), 0)
                qty = int(c.get('qty') or c.get('quantity') or 1)
                if not name:
                    if is_json:
                        return JsonResponse({'success': False, 'error': 'Cart item missing name.'}, status=400)
                    messages.error(request, 'One of the cart items is missing a name.')
                    return redirect('cart_page')
                order = Order.objects.create(
                    item=name,
                    price=price,
                    qty=qty,
                    order_type=order_type,
                    order_date=order_date,
                    order_time=order_time,
                    email=email,
                    mobile=mobile,
                    address=address,
                    delivery=delivery,
                )
                created_ids.append(order.id)
        else:
            # Single item flow (form or JSON)
            item = data.get('item') or data.get('name')
            price = _num(data.get('price') or data.get('amount'), 0)
            qty = int(data.get('qty') or data.get('quantity') or 1)
            mobile = data.get('mobile') or data.get('phone') or ''
            address = data.get('address') or ''
            delivery = data.get('delivery') or ''
            order_type = data.get('orderType') or data.get('order_type') or 'now'
            order_date = data.get('orderDate') if order_type == 'later' else None
            order_time = data.get('orderTime') if order_type == 'later' else None

            # Validate required fields
            if not all([item, price is not None, qty, mobile, address, delivery]):
                if is_json:
                    return JsonResponse({'success': False, 'error': 'Missing required fields.'}, status=400)
                messages.error(request, 'Please fill all required order fields.')
                return redirect('cart_page')

            order = Order.objects.create(
                item=item,
                price=price,
                qty=qty,
                order_type=order_type,
                order_date=order_date,
                order_time=order_time,
                email=email,
                mobile=mobile,
                address=address,
                delivery=delivery,
            )
            created_ids.append(order.id)

        # store created ids in session so cart.html can show last successful order(s)
        request.session['last_order_ids'] = created_ids

        if is_json:
            return JsonResponse({'success': True, 'order_ids': created_ids})
        else:
            messages.success(request, 'Order placed successfully.')
            return redirect('cart_page')

    except Exception as e:
        # Log the error and respond appropriately
        # (keep server-rendered behavior friendly)
        if is_json:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
        messages.error(request, f'Failed to place order: {e}')
        return redirect('cart_page')

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
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
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
            reason = request.POST.get('reason')
            order.status = 'Cancelled'
            order.cancellation_reason = reason
            order.save()
            # Robust AJAX detection: allow either header key variant
            is_ajax = (
                request.headers.get('x-requested-with') == 'XMLHttpRequest' or
                request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
            )
            if is_ajax:
                return JsonResponse({'status': 'success', 'reason': reason})
            return redirect('order_food_table')

    # If not POST or unknown action, respond for AJAX
    is_ajax_req = (
        request.headers.get('x-requested-with') == 'XMLHttpRequest' or
        request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
    )
    if is_ajax_req:
        return JsonResponse({'status': 'error', 'message': 'Invalid request method or action'}, status=400)
        
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
    
    return render(request, 'admin2/order_food_table.html', {
        'orders': orders,
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

@login_required
def order_card_list(request):
    orders = Order.objects.filter(email=request.user.email).order_by('-created_at')
    return render(request, 'order_card_list.html', {'orders': orders})

@login_required
def order_card_detail(request, pk):
    order = get_object_or_404(Order, pk=pk, email=request.user.email)
    
    steps = ['pending', 'Accepted', 'Making', 'Ready to Collect', 'Delivered']
    
    try:
        current_step_index = steps.index(order.status)
    except ValueError:
        current_step_index = -1

    context = {
        'order': order,
        'steps': steps,
        'current_step_index': current_step_index,
    }
    return render(request, 'order_card_detail.html', context)


def cart_page(request):
    """
    Renders cart page. When coming from a successful order_submit (form), the
    created order ids are saved in session['last_order_ids'] and displayed here
    as last_orders (then removed from session).
    """
    last_orders = []
    last_ids = request.session.pop('last_order_ids', None)
    if last_ids:
        last_orders = list(Order.objects.filter(id__in=last_ids).order_by('-created_at'))
    return render(request, 'cart.html', {'last_orders': last_orders})

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

@login_required
def send_confirmation_email(request, pk):
    if not request.user.is_staff:
        return redirect('admin_login')
        
    reservation = get_object_or_404(TableReservation, pk=pk)
    
    subject = f'Your table reservation for {reservation.date} is confirmed'
    message = f'Dear {reservation.name},\n\nYour table reservation for {reservation.date} at {reservation.time} has been confirmed.'
    try:
        send_mail(subject, message, 'saranvignesh55@gmail.com', [reservation.email])
        messages.success(request, f'Confirmation email sent to {reservation.email}.')
    except Exception as e:
        messages.error(request, f'Failed to send confirmation email: {str(e)}')
            
    return redirect('admin_reservations')