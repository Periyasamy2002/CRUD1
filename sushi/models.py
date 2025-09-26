from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

class CustomUserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        if not username:
            raise ValueError('Username is required')
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, username, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    USER_TYPE_CHOICES = (
        ('customer', 'Customer'),
        ('management', 'Management'),
    )
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='customer')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'username'  # <-- Change here
    REQUIRED_FIELDS = ['email']  # <-- Change here

    objects = CustomUserManager()

    def __str__(self):
        return self.email

# ---------------- Menu Category ----------------
class MenuCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    added_by = models.CharField(max_length=100, default='admin')

    def __str__(self):
        return self.name

# ---------------- Menu Item ----------------
class MenuItem(models.Model):
    category = models.ForeignKey(MenuCategory, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    image = models.ImageField(upload_to='menu_images/', blank=True, null=True)
    featured = models.BooleanField(default=False)

    def __str__(self):
        return self.name

# ---------------- Special Menu ----------------
class SpecialMenu(models.Model):
    image = models.ImageField(upload_to='special_menu/')
    title = models.CharField(max_length=100)
    subtitle = models.CharField(max_length=200, blank=True)
    price = models.DecimalField(max_digits=7, decimal_places=2)

    def __str__(self):
        return self.title

# ---------------- Order ----------------
class Order(models.Model):
    ORDER_TYPE_CHOICES = [
        ('now', 'Order Now'),
        ('later', 'Order Later'),
    ]
    DELIVERY_CHOICES = [
        ('Click & Collect', 'Click & Collect (Free)'),
        ('Free', 'Free'),
        ('Livraison Express 3.5km', 'Livraison Express 3.5km'),
    ]
    item = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=7, decimal_places=2)
    qty = models.PositiveIntegerField()
    order_type = models.CharField(max_length=10, choices=ORDER_TYPE_CHOICES)
    order_date = models.DateField(null=True, blank=True)
    order_time = models.TimeField(null=True, blank=True)
    email = models.EmailField()
    mobile = models.CharField(max_length=30)
    address = models.CharField(max_length=255)
    delivery = models.CharField(max_length=40, choices=DELIVERY_CHOICES)
    created_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=30, default='pending')

    def __str__(self):
        return f"{self.item} x{self.qty} ({self.email})"

# If you want to add a custom admin model, you can do so like this:
# from django.contrib.auth.models import AbstractUser
# class CustomAdminUser(AbstractUser):
#     # Add custom fields if needed
#     pass
