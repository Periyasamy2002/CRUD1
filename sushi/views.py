from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .models import MenuCategory, MenuItem, SpecialMenu
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.contrib import messages

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
    return render(request, 'menu.html', {'menuitems': menuitems})



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

        return redirect('contact')  # Change to your contact page URL name

    return render(request, 'contact.html')

def table_reservation(request):
    return render(request, 'reservation.html')

def order_menu(request):
    return render(request, 'order_menu.html')


# ---------------- Admin: Create Menu Item ----------------

@login_required
def menuitem_create(request):
    if not request.user.is_staff:
        return redirect('admin_login')

    categories = MenuCategory.objects.all()
    error_message = None

    if request.method == 'POST':
        category_id = request.POST.get('category')
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        price = request.POST.get('price')
        image = request.FILES.get('image')

        try:
            category = MenuCategory.objects.get(id=category_id)
            MenuItem.objects.create(
                category=category,
                name=name,
                description=description,
                price=price,
                image=image
            )
            return redirect('menuitem_list')
        except MenuCategory.DoesNotExist:
            error_message = "Selected category does not exist."

    return render(request, 'admin/menuitem_form.html', {
        'categories': categories,
        'error_message': error_message
    })


# ---------------- Admin: List Menu Items ----------------

@login_required
def menuitem_list(request):
    if not request.user.is_staff:
        return redirect('admin_login')

    menuitems = MenuItem.objects.all()
    categories = MenuCategory.objects.all()
    error_message = request.GET.get('error_message', None)
    return render(request, 'menuitem_list.html', {
        'menuitems': menuitems,
        'categories': categories,
        'error_message': error_message
    })


# ---------------- Admin Login ----------------

def admin_login(request):
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


# ---------------- Admin: Edit Menu Item ----------------

@login_required
def menuitem_edit(request, item_id):
    if not request.user.is_staff:
        return redirect('admin_login')

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

    return render(request, 'admin/menuitem_form.html', {
        'item': item,
        'categories': categories
    })


# ---------------- Admin: Delete Menu Item ----------------

@login_required
def menuitem_delete(request, item_id):
    if not request.user.is_staff:
        return redirect('admin_login')

    item = get_object_or_404(MenuItem, id=item_id)

    if request.method == 'POST':
        item.delete()
        return redirect('menuitem_list')

    return render(request, 'sushi/menuitem_confirm_delete.html', {'item': item})


# ---------------- Public Login View ----------------

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            auth_login(request, user)
            if user.is_staff:
                return redirect('menuitem_list')  # Admin dashboard
            else:
                return redirect('home')  # Public user homepage
        else:
            return render(request, 'login.html', {'error': 'Invalid username or password'})
    
    return render(request, 'login.html')


# ---------------- Admin: Create Category ----------------

@csrf_exempt
def category_create(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        added_by = request.POST.get('added_by')
        if name and added_by:
            MenuCategory.objects.create(name=name)
            return JsonResponse({'success': True})
        return JsonResponse({'success': False, 'error': 'Missing fields'})
    return JsonResponse({'success': False, 'error': 'Invalid request'})

# ---------------- Admin: Edit Menu Item (AJAX support) ----------------

@login_required
def menuitem_edit(request, item_id):
    if not request.user.is_staff:
        return redirect('admin_login')

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
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        return redirect('menuitem_list')

    return render(request, 'admin/menuitem_form.html', {
        'item': item,
        'categories': categories
    })