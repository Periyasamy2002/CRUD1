from django.db import models

class MenuCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class MenuItem(models.Model):
    category = models.ForeignKey(MenuCategory, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)  # <-- Add this line
    price = models.DecimalField(max_digits=6, decimal_places=2)
    image = models.ImageField(upload_to='menu_images/', blank=True, null=True)
    featured = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class SpecialMenu(models.Model):
    image = models.ImageField(upload_to='special_menu/')
    title = models.CharField(max_length=100)
    subtitle = models.CharField(max_length=200, blank=True)
    price = models.DecimalField(max_digits=7, decimal_places=2)

    def __str__(self):
        return self.title
