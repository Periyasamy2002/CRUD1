from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
import calendar

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
    cancellation_reason = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.item} x{self.qty} ({self.email})"

    @property
    def total_price(self):
        return self.price * self.qty

    def get_formatted_date(self):
        """Return formatted date for display"""
        if self.order_date:
            return self.order_date.strftime("%d %b %Y")
        return self.created_at.strftime("%d %b %Y")

    def get_formatted_time(self):
        """Return formatted time for display"""
        if self.order_time:
            return self.order_time.strftime("%I:%M %p")
        return self.created_at.strftime("%I:%M %p")

    # Added helper to return a simple dict for templates / debugging
    def to_dict(self):
        return {
            "id": self.id,
            "item": self.item,
            "price": str(self.price),
            "qty": self.qty,
            "total_price": str(self.total_price),
            "order_type": self.order_type,
            "order_date": self.order_date.isoformat() if self.order_date else None,
            "order_time": self.order_time.isoformat() if self.order_time else None,
            "email": self.email,
            "mobile": self.mobile,
            "address": self.address,
            "delivery": self.delivery,
            "created_at": self.created_at.isoformat(),
            "status": self.status,
            "formatted_date": self.get_formatted_date(),
            "formatted_time": self.get_formatted_time(),
            "formatted_created": self.created_at.strftime("%d %b %Y %I:%M %p"),
        }

    @classmethod
    def dashboard_summary(cls, months=6):
        """Enhanced dashboard summary with better date handling"""
        now = timezone.now()
        today = now.date()
        
        # Get basic counts
        summary = {
            "total_orders": cls.objects.count(),
            "today_orders": cls.objects.filter(created_at__date=today).count(),
            "pending_orders": cls.objects.filter(status__iexact='pending').count(),
            "delivered_orders": cls.objects.filter(status__iexact='delivered').count(),
        }

        # Calculate revenue
        revenue_expr = ExpressionWrapper(F('price') * F('qty'), output_field=DecimalField())
        
        # Total revenue
        agg = cls.objects.aggregate(total_revenue=Sum(revenue_expr))
        summary["total_revenue"] = float(agg.get('total_revenue') or 0.0)
        
        # Today's revenue
        today_agg = cls.objects.filter(created_at__date=today).aggregate(
            today_revenue=Sum(revenue_expr)
        )
        summary["today_revenue"] = float(today_agg.get('today_revenue') or 0.0)

        # Recent orders with better formatting
        recent_orders = []
        for o in cls.objects.order_by('-created_at')[:10]:
            recent_orders.append({
                "id": o.id,
                "customer_name": o.email.split('@')[0] if o.email else "unknown",
                "total_amount": float(o.total_price),
                "status": o.status.title(),
                "date": o.get_formatted_date(),
                "time": o.get_formatted_time(),
                "created_at": o.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            })
        summary["recent_orders"] = recent_orders

        # Monthly chart data with proper date formatting
        months_data = []
        for i in range(months-1, -1, -1):
            target_date = now - timezone.timedelta(days=i*30)
            month_total = cls.objects.filter(
                created_at__year=target_date.year,
                created_at__month=target_date.month
            ).aggregate(
                month_total=Sum(revenue_expr)
            )['month_total'] or 0
            
            months_data.append({
                "label": target_date.strftime("%b %Y"),
                "value": float(month_total)
            })

        summary["chart_data"] = {
            "labels": [m["label"] for m in months_data],
            "values": [m["value"] for m in months_data]
        }

        return summary

# ---------------- Contact ----------------
class Contact(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='pending', choices=[
        ('pending', 'Pending'),
        ('responded', 'Responded'),
    ])

    def __str__(self):
        return f"{self.name} - {self.created_at.date()}"

class TableReservation(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    date = models.DateField()
    time = models.TimeField()
    guests = models.PositiveSmallIntegerField()
    special_requests = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, default='pending', choices=[
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ])
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.date} {self.time}"

# If you want to add a custom admin model, you can do so like this:
# from django.contrib.auth.models import AbstractUser
# class CustomAdminUser(AbstractUser):
#     # Add custom fields if needed
#     pass
