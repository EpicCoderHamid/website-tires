from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.urls import reverse

class Brand(models.Model):
    name = models.CharField(max_length=100)
    logo = models.ImageField(upload_to='brand_logos/', null=True, blank=True)
    
    def __str__(self):
        return self.name

class CarBrand(models.Model):
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name

class CarModel(models.Model):
    brand = models.ForeignKey(CarBrand, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    year = models.IntegerField()
    rim_size = models.DecimalField(max_digits=3, decimal_places=1)  # e.g., 16.0, 17.5
    
    class Meta:
        unique_together = ['brand', 'name', 'year']
    
    def __str__(self):
        return f"{self.brand.name} {self.name} {self.year}"

class Tire(models.Model):
    TIRE_TYPES = [
        ('summer', 'Summer'),
        ('winter', 'Winter'),
        ('all_season', 'All Season'),
        ('performance', 'Performance'),
    ]
    
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    rim_size = models.DecimalField(max_digits=3, decimal_places=1)
    width = models.IntegerField()  # e.g., 205, 225
    aspect_ratio = models.IntegerField()  # e.g., 55, 65
    tire_type = models.CharField(max_length=20, choices=TIRE_TYPES)
    image = models.ImageField(upload_to='tire_images/', null=True, blank=True)
    stock_quantity = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Compatibility with car models
    compatible_cars = models.ManyToManyField(CarModel, blank=True)
    
    def __str__(self):
        return f"{self.brand.name} {self.name} {self.width}/{self.aspect_ratio}R{self.rim_size}"
    
    def get_tire_size(self):
        return f"{self.width}/{self.aspect_ratio}R{self.rim_size}"

class Cart(models.Model):
    # Allow anonymous carts by making user optional
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())
    
    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    def __str__(self):
        if self.user:
            return f"Cart #{self.id} (user={self.user.username})"
        return f"Cart #{self.id} (anonymous)"

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    tire = models.ForeignKey(Tire, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    
    class Meta:
        unique_together = ['cart', 'tire']
    
    @property
    def total_price(self):
        return self.tire.price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.tire} (cart {self.cart_id})"

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    # allow null user to support guest checkout
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    order_number = models.CharField(max_length=20, unique=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    # Customer details
    customer_name = models.CharField(max_length=255, null=True, blank=True)
    customer_email = models.EmailField(null=True, blank=True)
    customer_city = models.CharField(max_length=255, null=True, blank=True)
    customer_phone = models.CharField(max_length=50, blank=True, null=True)
    shipping_address = models.TextField(null=True, blank=True)

    # PAYMENT METHOD (nullable so migrations are safe)
    payment_method = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return f"Order {self.order_number}"

    def get_absolute_url(self):
        return reverse('order_detail', args=[self.pk])
class Product(models.Model):
    image = models.ImageField(upload_to='products/%Y/%m/%d/', blank=True, null=True)
    # ...

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    tire = models.ForeignKey(Tire, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    @property
    def total_price(self):
        return self.price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.tire} (order {self.order.order_number})"
