from django.urls import path
from . import views

# Admin site customization
from django.contrib import admin
admin.site.site_header = "Hamid Admin Web"
admin.site.site_title = " Hamid Admin Portal"
admin.site.index_title = "Welcome to Hamid"

urlpatterns = [
    # Home & Tire Pages
    path("", views.home, name="home"),
    path("tires/", views.tire_list, name="tire_list"),
    path("tires/<int:tire_id>/", views.tire_detail, name="tire_detail"),
    path("find-by-car/", views.find_tires_by_car, name="find_tires_by_car"),

    # Cart System
    path("cart/", views.view_cart, name="view_cart"),
    path("cart/add/<int:tire_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/update/<int:item_id>/", views.update_cart_item, name="update_cart_item"),
    path("cart/remove/<int:item_id>/", views.remove_from_cart, name="remove_from_cart"),

    # Checkout
    path("checkout/", views.checkout, name="checkout"),
    path("order-confirmation/<int:order_id>/", views.order_confirmation, name="order_confirmation"),

    # Order System
    path("orders/", views.order_list, name="order_list"),
    path("orders/<int:order_id>/", views.order_detail, name="order_detail"),
    path("orders/<int:order_id>/tracking/", views.order_tracking, name="order_tracking"),

    # Public Order Tracking
    path("order-search/", views.order_search, name="order_search"),
    path("track-order/<str:order_number>/", views.public_order_tracking, name="public_order_tracking"),

    # TODO (I will add these for email/payment handling in your views.py next)
    # path("payment/<int:order_id>/card/", views.card_payment_page, name="card_payment"),
    # path("payment/<int:order_id>/paypal/", views.paypal_redirect, name="paypal_redirect"),
]
