from django.contrib import admin
from django.http import HttpResponse
from django.utils.html import format_html
import csv

from .models import (
    Brand, CarBrand, CarModel,
    Tire, Cart, CartItem,
    Order, OrderItem
)


# ---------------------------
# Inline classes
# ---------------------------
class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('total_price_display',)
    fields = ('tire', 'quantity', 'total_price_display')
    autocomplete_fields = ('tire',)

    def total_price_display(self, obj):
        try:
            return f"{obj.total_price:.2f}"
        except Exception:
            return "-"
    total_price_display.short_description = "Total"


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('total_price_display',)
    fields = ('tire', 'quantity', 'price', 'total_price_display')
    autocomplete_fields = ('tire',)

    def total_price_display(self, obj):
        try:
            return f"{obj.total_price:.2f}"
        except Exception:
            return "-"
    total_price_display.short_description = "Total"


# ---------------------------
# Brand admin
# ---------------------------
@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'logo_preview')
    readonly_fields = ('logo_preview',)
    search_fields = ('name',)

    def logo_preview(self, obj):
        if obj.logo:
            return format_html('<img src="{}" style="height:60px;"/>', obj.logo.url)
        return "(No logo)"
    logo_preview.short_description = 'Logo'


# ---------------------------
# CarBrand & CarModel admin
# ---------------------------
@admin.register(CarBrand)
class CarBrandAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


@admin.register(CarModel)
class CarModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'brand', 'name', 'year', 'rim_size')
    list_filter = ('brand', 'year')
    search_fields = ('brand__name', 'name', 'year')
    autocomplete_fields = ('brand',)


# ---------------------------
# Tire admin
# ---------------------------
@admin.register(Tire)
class TireAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'name', 'brand', 'tire_size_display',
        'tire_type', 'price', 'stock_quantity', 'created_at', 'image_preview'
    )
    list_filter = ('brand', 'tire_type', 'rim_size', 'created_at')
    search_fields = ('name', 'brand__name', 'width', 'aspect_ratio', 'rim_size')
    list_editable = ('price', 'stock_quantity')
    readonly_fields = ('created_at', 'image_preview')
    filter_horizontal = ('compatible_cars',)
    autocomplete_fields = ('brand',)
    fieldsets = (
        (None, {
            'fields': ('brand', 'name', 'description', 'image', 'image_preview')
        }),
        ('Specs & Pricing', {
            'fields': ('width', 'aspect_ratio', 'rim_size', 'tire_type', 'price', 'stock_quantity')
        }),
        ('Compatibility', {
            'fields': ('compatible_cars',)
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )

    def tire_size_display(self, obj):
        try:
            return obj.get_tire_size()
        except Exception:
            return f"{obj.width}/{obj.aspect_ratio}R{obj.rim_size}"
    tire_size_display.short_description = "Size"

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:80px;"/>', obj.image.url)
        return "(No image)"
    image_preview.short_description = "Image"


# ---------------------------
# Cart & CartItem admin
# ---------------------------
@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_display', 'total_items', 'total_price_display', 'updated_at')
    readonly_fields = ('created_at', 'updated_at',)
    inlines = [CartItemInline]
    search_fields = ('user__username', 'user__email')

    def user_display(self, obj):
        return obj.user.username if obj.user else "Anonymous"
    user_display.short_description = "User"

    def total_price_display(self, obj):
        try:
            return f"{obj.total_price:.2f}"
        except Exception:
            return "0.00"
    total_price_display.short_description = "Total Price"


# ---------------------------
# Order & OrderItem admin
# ---------------------------
def export_orders_csv(modeladmin, request, queryset):
    """Admin action: export selected orders as CSV"""
    fieldnames = [
        'order_number', 'user', 'customer_name', 'customer_email',
        'status', 'total_amount', 'created_at', 'customer_phone', 'customer_city', 'shipping_address'
    ]
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=orders.csv'
    writer = csv.DictWriter(response, fieldnames=fieldnames)
    writer.writeheader()
    for order in queryset:
        writer.writerow({
            'order_number': order.order_number,
            'user': order.user.username if order.user else '',
            'customer_name': order.customer_name,
            'customer_email': order.customer_email,
            'status': order.status,
            'total_amount': f"{order.total_amount:.2f}",
            'created_at': order.created_at.isoformat(),
            'customer_phone': order.customer_phone,
            'customer_city': order.customer_city,
            'shipping_address': order.shipping_address,
        })
    return response
export_orders_csv.short_description = "Export selected orders to CSV"


def mark_orders_shipped(modeladmin, request, queryset):
    updated = queryset.update(status='shipped')
    modeladmin.message_user(request, f"{updated} order(s) marked as shipped.")
mark_orders_shipped.short_description = "Mark selected orders as Shipped"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user_display', 'status', 'total_amount', 'created_at', 'customer_name')
    list_filter = ('status', 'created_at')
    search_fields = ('order_number', 'user__username', 'customer_email', 'customer_phone', 'customer_name')
    readonly_fields = ('created_at',)
    inlines = [OrderItemInline]
    autocomplete_fields = ('user',)
    actions = (mark_orders_shipped, export_orders_csv)
    fieldsets = (
        (None, {
            'fields': ('order_number', 'user', 'status', 'total_amount', 'payment_method')
        }),
        ('Customer details', {
            'fields': ('customer_name', 'customer_email', 'customer_phone', 'customer_city', 'shipping_address')
        }),
        ('Dates', {
            'fields': ('created_at',)
        }),
    )

    def user_display(self, obj):
        return obj.user.username if obj.user else "Guest"
    user_display.short_description = "User"


# ---------------------------
# Register OrderItem separately so it is searchable too
# ---------------------------
@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'tire', 'quantity', 'price', 'total_price_display')
    search_fields = ('order__order_number', 'tire__name', 'tire__brand__name')
    readonly_fields = ('total_price_display',)

    def total_price_display(self, obj):
        try:
            return f"{obj.total_price:.2f}"
        except Exception:
            return "-"
    total_price_display.short_description = "Total"


# ---------------------------
# Keep CarBrand/CarModel registered (already above) but register CartItem for direct access too
# ---------------------------
@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'cart', 'tire', 'quantity', 'total_price_display')
    search_fields = ('cart__id', 'tire__name', 'tire__brand__name')
    readonly_fields = ('total_price_display',)

    def total_price_display(self, obj):
        try:
            return f"{obj.total_price:.2f}"
        except Exception:
            return "-"
    total_price_display.short_description = "Total"
