from decimal import Decimal
import time

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.db.models import Q
from django.core.paginator import Paginator
from django.utils.crypto import get_random_string

from .models import *
from .forms import *


# Session key for anonymous cart
SESSION_CART_KEY = 'cart_id'
SESSION_LAST_ORDER = 'last_order_id'


# -------------------------
# Helper: get or create cart (supports anonymous + logged-in)
# -------------------------
def get_cart(request):
    """
    Return Cart instance for request:
     - If user is authenticated: return or create cart linked to user.
     - Else: return or create anonymous cart and store its id in session.
    """
    user = getattr(request, 'user', None)
    if user and user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=user)
        return cart

    # anonymous cart via session
    cart_id = request.session.get(SESSION_CART_KEY)
    if cart_id:
        try:
            cart = Cart.objects.get(id=cart_id, user__isnull=True)
            return cart
        except Cart.DoesNotExist:
            pass

    cart = Cart.objects.create()
    request.session[SESSION_CART_KEY] = cart.id
    request.session.modified = True
    return cart


# -------------------------
# Home & tires
# -------------------------
def home(request):
    brands = Brand.objects.all()[:10]
    featured_tires = Tire.objects.filter(stock_quantity__gt=0)[:8]

    return render(request, 'tires/home.html', {
        'brands': brands,
        'featured_tires': featured_tires
    })


def tire_list(request):
    tires = Tire.objects.filter(stock_quantity__gt=0)

    # Filtering
    brand_filter = request.GET.get('brand')
    rim_size_filter = request.GET.get('rim_size')
    tire_type_filter = request.GET.get('tire_type')

    if brand_filter:
        tires = tires.filter(brand__name__icontains=brand_filter)
    if rim_size_filter:
        try:
            tires = tires.filter(rim_size=float(rim_size_filter))
        except ValueError:
            pass
    if tire_type_filter:
        tires = tires.filter(tire_type=tire_type_filter)

    brands = Brand.objects.all()
    rim_sizes = Tire.objects.values_list('rim_size', flat=True).distinct()

    return render(request, 'tires/tire_list.html', {
        'tires': tires,
        'brands': brands,
        'rim_sizes': rim_sizes,
        'TIRE_TYPES': Tire.TIRE_TYPES
    })


def tire_detail(request, tire_id):
    tire = get_object_or_404(Tire, id=tire_id)
    compatible_cars = tire.compatible_cars.all()[:10]
    similar_tires = Tire.objects.filter(
        rim_size=tire.rim_size
    ).exclude(id=tire.id).filter(stock_quantity__gt=0)[:4]

    return render(request, 'tires/tire_detail.html', {
        'tire': tire,
        'compatible_cars': compatible_cars,
        'similar_tires': similar_tires
    })


def find_tires_by_car(request):
    form = CarSearchForm()
    tires = None
    car_model = None
    search_performed = False

    if request.method == 'GET' and any(k in request.GET for k in ['car_brand', 'car_model', 'year']):
        form = CarSearchForm(request.GET)
        search_performed = True

        # Debug: Print what we received
        print(f"DEBUG - Received GET data: {dict(request.GET)}")

        if form.is_valid():
            car_brand = form.cleaned_data['car_brand']
            car_model_name = form.cleaned_data['car_model']
            year = form.cleaned_data['year']

            # Debug: Print cleaned data
            print(f"DEBUG - Cleaned data - Brand: '{car_brand}', Model: '{car_model_name}', Year: {year}")

            # Find matching car model - use exact matching for better results
            car_model = CarModel.objects.filter(
                brand__name__iexact=car_brand.strip(),
                name__iexact=car_model_name.strip(),
                year=year
            ).first()

            # Debug: Print search results
            print(f"DEBUG - Car model found: {car_model}")

            if car_model:
                tires = Tire.objects.filter(
                    rim_size=car_model.rim_size,
                    stock_quantity__gt=0
                )
                messages.success(request, f"Found {tires.count()} tires for {car_brand} {car_model_name} {year}")
                print(f"DEBUG - Found {tires.count()} tires with rim size: {car_model.rim_size}")
            else:
                # Show helpful error message with available options
                available_brands = CarBrand.objects.all().values_list('name', flat=True)
                similar_models = CarModel.objects.filter(
                    brand__name__iexact=car_brand.strip()
                ).values_list('name', flat=True).distinct() if car_brand else []

                # Check if brand exists
                brand_exists = CarBrand.objects.filter(name__iexact=car_brand.strip()).exists()

                if not brand_exists:
                    error_msg = f"Brand '{car_brand}' not found. Available brands: {', '.join(available_brands)}"
                elif similar_models:
                    # Get available years for this model
                    available_years = CarModel.objects.filter(
                        brand__name__iexact=car_brand.strip(),
                        name__iexact=car_model_name.strip()
                    ).values_list('year', flat=True).distinct()
                    if available_years:
                        error_msg = f"Model '{car_brand} {car_model_name}' found but not for year {year}. Available years: {', '.join(map(str, available_years))}"
                    else:
                        error_msg = f"Model '{car_model_name}' not found for brand '{car_brand}'. Available models: {', '.join(similar_models)}"
                else:
                    error_msg = f"Brand '{car_brand}' found but no models available. Available brands: {', '.join(available_brands)}"

                messages.warning(request, error_msg)
                print(f"DEBUG - Error: {error_msg}")
        else:
            # Form validation failed
            print(f"DEBUG - Form errors: {form.errors}")
            messages.error(request, "Please check your input. All fields are required and year must be between 1990-2025.")

    return render(request, 'tires/find_by_car.html', {
        'form': form,
        'tires': tires,
        'car_model': car_model,
        'search_performed': search_performed
    })


def debug_car_search(request):
    """Debug view to check car models in database"""
    brand = request.GET.get('brand', 'Honda')
    model = request.GET.get('model', 'City')
    year = request.GET.get('year', '2020')

    try:
        year = int(year)
    except (ValueError, TypeError):
        year = 2020

    # Check exact matches
    exact_match = CarModel.objects.filter(
        brand__name__iexact=brand,
        name__iexact=model,
        year=year
    ).first()

    # Check what's available
    all_brands = CarBrand.objects.all().values_list('name', flat=True)
    models_for_brand = CarModel.objects.filter(
        brand__name__iexact=brand
    ).values_list('name', 'year', 'rim_size').distinct() if brand else []

    years_for_model = CarModel.objects.filter(
        brand__name__iexact=brand,
        name__iexact=model
    ).values_list('year', flat=True).distinct() if brand and model else []

    # Get sample data
    sample_cars = CarModel.objects.all()[:10].values('brand__name', 'name', 'year', 'rim_size')

    return JsonResponse({
        'search_params': {
            'brand': brand,
            'model': model,
            'year': year
        },
        'exact_match': {
            'found': exact_match is not None,
            'details': {
                'brand': exact_match.brand.name if exact_match else None,
                'model': exact_match.name if exact_match else None,
                'year': exact_match.year if exact_match else None,
                'rim_size': exact_match.rim_size if exact_match else None
            }
        },
        'available_brands': list(all_brands),
        'models_for_brand': list(models_for_brand),
        'years_for_model': list(years_for_model),
        'total_car_models': CarModel.objects.count(),
        'total_car_brands': CarBrand.objects.count(),
        'sample_cars': list(sample_cars)
    })


# -------------------------
# Cart endpoints (supporting anonymous)
# -------------------------
def add_to_cart(request, tire_id):
    tire = get_object_or_404(Tire, id=tire_id)

    if request.method == 'POST':
        try:
            quantity = int(request.POST.get('quantity', 1))
        except (ValueError, TypeError):
            quantity = 1

        if quantity > tire.stock_quantity:
            messages.error(request, "Requested quantity exceeds available stock.")
            return redirect('tire_detail', tire_id=tire_id)

        cart = get_cart(request)
        cart_item, item_created = CartItem.objects.get_or_create(
            cart=cart,
            tire=tire,
            defaults={'quantity': quantity}
        )

        if not item_created:
            # Don't exceed available stock when updating existing item
            new_quantity = cart_item.quantity + quantity
            if new_quantity > tire.stock_quantity:
                messages.error(request, "Cannot add more than available stock.")
                return redirect('view_cart')
            cart_item.quantity = new_quantity
            cart_item.save()

        messages.success(request, f"Added {quantity} {tire.name} to cart.")
        return redirect('view_cart')

    return redirect('tire_detail', tire_id=tire_id)


def view_cart(request):
    cart = get_cart(request)
    return render(request, 'tires/cart.html', {
        'cart': cart
    })


def update_cart_item(request, item_id):
    """
    Update a CartItem's quantity. Accepts POST only.
    Ensures item belongs to the current cart (session or user).
    """
    try:
        cart_item = CartItem.objects.get(id=item_id)
    except CartItem.DoesNotExist:
        return HttpResponseBadRequest("Item does not exist")

    cart = get_cart(request)
    if cart_item.cart_id != cart.id:
        return HttpResponseForbidden("This item is not in your cart")

    if request.method == 'POST':
        try:
            quantity = int(request.POST.get('quantity', cart_item.quantity))
        except (ValueError, TypeError):
            quantity = cart_item.quantity

        if quantity <= 0:
            cart_item.delete()
            messages.success(request, "Item removed from cart.")
        elif quantity > cart_item.tire.stock_quantity:
            messages.error(request, "Requested quantity exceeds available stock.")
        else:
            cart_item.quantity = quantity
            cart_item.save()
            messages.success(request, "Cart updated successfully.")

    return redirect('view_cart')


def remove_from_cart(request, item_id):
    try:
        cart_item = CartItem.objects.get(id=item_id)
    except CartItem.DoesNotExist:
        return HttpResponseBadRequest("Item does not exist")

    cart = get_cart(request)
    if cart_item.cart_id != cart.id:
        return HttpResponseForbidden("This item is not in your cart")

    cart_item.delete()
    messages.success(request, "Item removed from cart.")
    return redirect('view_cart')


# -------------------------
# Helper to build shipping address
# -------------------------
def build_shipping_address(data: dict) -> str:
    """
    Helper to build a single shipping_address string from customer details form data.
    The CustomerDetailsForm stores address pieces in session keys like:
    apartment_suite, street_address, town_city, state_province, postal_code, country
    """
    parts = []
    if data.get('apartment_suite'):
        parts.append(data.get('apartment_suite'))
    if data.get('street_address'):
        parts.append(data.get('street_address'))
    # prefer 'town_city' from the form; if not present, fall back to 'customer_city'
    town = data.get('town_city') or data.get('customer_city')
    if town:
        parts.append(town)
    if data.get('state_province'):
        parts.append(data.get('state_province'))
    if data.get('postal_code'):
        parts.append(data.get('postal_code'))
    if data.get('country'):
        parts.append(data.get('country'))
    return ", ".join(parts)


# -------------------------
# Checkout: supports guest checkout
# -------------------------
def checkout(request):
    cart = get_cart(request)

    if cart.total_items == 0:
        messages.warning(request, "Your cart is empty.")
        return redirect('view_cart')

    # Check stock availability before checkout
    for item in cart.items.all():
        if item.quantity > item.tire.stock_quantity:
            messages.error(request, f"Sorry, only {item.tire.stock_quantity} of {item.tire.name} available.")
            return redirect('view_cart')

    # Step 1: Customer Details
    if request.method == 'POST' and 'customer_details' in request.POST:
        customer_form = CustomerDetailsForm(request.POST)
        payment_form = PaymentForm()

        if customer_form.is_valid():
            # Store customer details in session
            request.session['customer_details'] = customer_form.cleaned_data
            request.session.modified = True
            messages.success(request, "Customer details saved. Please select payment method.")

            return render(request, 'tires/checkout.html', {
                'cart': cart,
                'customer_form': customer_form,
                'payment_form': payment_form,
                'step': 'payment'
            })
        else:
            # If form is invalid, show errors
            payment_form = PaymentForm()
            return render(request, 'tires/checkout.html', {
                'cart': cart,
                'customer_form': customer_form,
                'payment_form': payment_form,
                'step': 'customer_details'
            })

    # Step 2: Payment Method & Create Order
    elif request.method == 'POST' and request.POST.get('step') == 'payment':
        # DEBUG: print POST to terminal for troubleshooting
        print("POST data (payment step):", dict(request.POST))

        customer_details = request.session.get('customer_details')

        if not customer_details:
            messages.error(request, "Please fill in your customer details first.")
            return redirect('checkout')

        payment_form = PaymentForm(request.POST)
        customer_form = CustomerDetailsForm(initial=customer_details)

        if payment_form.is_valid():
            # Build shipping_address string from stored customer details
            shipping_address = build_shipping_address(customer_details)

            # Create order with all details
            order = Order(
                user=request.user if request.user.is_authenticated else None,
                total_amount=cart.total_price if isinstance(cart.total_price, Decimal) else Decimal(str(cart.total_price)),
                order_number=get_random_string(10).upper(),
                payment_method=payment_form.cleaned_data['payment_method'],
                # Customer details
                customer_name=customer_details.get('customer_name', ''),
                customer_email=customer_details.get('customer_email', ''),
                customer_phone=customer_details.get('customer_phone', ''),
                customer_city=customer_details.get('town_city') or customer_details.get('customer_city', ''),
                # Shipping address (single text field)
                shipping_address=shipping_address
            )
            order.save()

            # Create order items and update stock
            for cart_item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    tire=cart_item.tire,
                    quantity=cart_item.quantity,
                    price=cart_item.tire.price
                )

                # Update stock
                cart_item.tire.stock_quantity -= cart_item.quantity
                cart_item.tire.save()

            # Clear cart items and session
            cart.items.all().delete()
            if 'customer_details' in request.session:
                del request.session['customer_details']

            # store last order id for anonymous user so they can view confirmation
            request.session[SESSION_LAST_ORDER] = order.id
            request.session.modified = True

            messages.success(request, f"Order placed successfully! Order number: {order.order_number}")
            return redirect('order_confirmation', order_id=order.id)
        else:
            # If payment form is invalid
            return render(request, 'tires/checkout.html', {
                'cart': cart,
                'customer_form': customer_form,
                'payment_form': payment_form,
                'step': 'payment'
            })

    # Initial load or GET request
    else:
        # Pre-fill with user data if available
        initial_data = {}
        if request.user.is_authenticated:
            initial_data = {
                'customer_name': f"{request.user.first_name} {request.user.last_name}".strip(),
                'customer_email': request.user.email,
            }

        customer_form = CustomerDetailsForm(initial=initial_data)
        payment_form = PaymentForm()

    return render(request, 'tires/checkout.html', {
        'cart': cart,
        'customer_form': customer_form,
        'payment_form': payment_form,
        'step': 'customer_details'
    })


def order_confirmation(request, order_id):
    """
    Allow page if:
      - order belongs to current user, or
      - order id matches last order id in session (for anonymous users), or
      - user is staff
    """
    order = get_object_or_404(Order, id=order_id)
    last_order = request.session.get(SESSION_LAST_ORDER)

    if request.user.is_staff:
        allowed = True
    elif order.user and request.user.is_authenticated:
        allowed = (order.user == request.user)
    else:
        # anonymous order -> allow if this session placed it
        allowed = (last_order == order.id)

    if not allowed:
        return HttpResponseForbidden("You are not allowed to view this order.")

    return render(request, 'tires/order_confirmation.html', {'order': order})


# -------------------------
# ORDER TRACKING VIEWS
# -------------------------
@login_required
def order_list(request):
    """Display all orders for the logged-in user"""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')

    # Pagination
    paginator = Paginator(orders, 10)  # 10 orders per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'tires/order_list.html', {
        'page_obj': page_obj,
        'orders': page_obj.object_list,
    })


@login_required
def order_detail(request, order_id):
    """Display detailed view of a specific order"""
    order = get_object_or_404(Order, id=order_id, user=request.user)

    return render(request, 'tires/order_detail.html', {
        'order': order
    })


def _build_status_timeline(current_status: str):
    """
    Helper to create a simple status timeline list of dicts:
    [{'status': 'pending', 'label': 'Pending', 'done': True/False}, ...]
    """
    choices = [c[0] for c in Order.STATUS_CHOICES]
    labels = {c[0]: c[1] for c in Order.STATUS_CHOICES}
    timeline = []
    for status in choices:
        timeline.append({
            'status': status,
            'label': labels.get(status, status.title()),
            'done': choices.index(status) <= choices.index(current_status)
        })
    return timeline


@login_required
def order_tracking(request, order_id):
    """Order tracking page with status progress"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    status_timeline = _build_status_timeline(order.status)

    return render(request, 'tires/order_tracking.html', {
        'order': order,
        'status_timeline': status_timeline
    })


# -------------------------
# ORDER SEARCH VIEWS (PUBLIC - NO LOGIN REQUIRED)
# -------------------------
def order_search(request):
    """Search for order by order number (public access)"""
    form = OrderSearchForm()
    orders = None
    search_performed = False

    if request.method == 'GET' and 'order_number' in request.GET:
        form = OrderSearchForm(request.GET)
        search_performed = True

        if form.is_valid():
            order_number = form.cleaned_data['order_number'].strip()
            # allow partial or full match (case-insensitive)
            orders = Order.objects.filter(order_number__icontains=order_number)
            if not orders.exists():
                messages.info(request, f"No orders found with order number: {order_number}")

    return render(request, 'tires/order_search.html', {
        'form': form,
        'orders': orders,
        'search_performed': search_performed
    })


def public_order_tracking(request, order_number):
    """Public order tracking page (no login required)"""
    try:
        order = Order.objects.get(order_number=order_number)
        status_timeline = _build_status_timeline(order.status)
        return render(request, 'tires/public_order_tracking.html', {
            'order': order,
            'status_timeline': status_timeline
        })
    except Order.DoesNotExist:
        messages.error(request, f"Order with number {order_number} not found.")
        return redirect('order_search')


# -------------------------
# API VIEWS FOR FRONTEND
# -------------------------
def api_car_brands(request):
    """API endpoint to get all car brands"""
    brands = CarBrand.objects.all().values_list('name', flat=True)
    return JsonResponse(list(brands), safe=False)


def api_car_models(request):
    """API endpoint to get models for a specific brand"""
    brand_name = request.GET.get('brand', '')
    if brand_name:
        models = CarModel.objects.filter(
            brand__name__iexact=brand_name
        ).values_list('name', flat=True).distinct()
        return JsonResponse(list(models), safe=False)
    return JsonResponse([], safe=False)


def api_car_years(request):
    """API endpoint to get years for a specific brand and model"""
    brand_name = request.GET.get('brand', '')
    model_name = request.GET.get('model', '')
    if brand_name and model_name:
        years = CarModel.objects.filter(
            brand__name__iexact=brand_name,
            name__iexact=model_name
        ).values_list('year', flat=True).distinct().order_by('year')
        return JsonResponse(list(years), safe=False)
    return JsonResponse([], safe=False)


def api_search_tires_by_car(request):
    """API endpoint for tire search by car"""
    if request.method == 'GET':
        brand_name = request.GET.get('brand', '').strip()
        model_name = request.GET.get('model', '').strip()
        year_str = request.GET.get('year', '').strip()

        if not all([brand_name, model_name, year_str]):
            return JsonResponse({
                'success': False,
                'message': 'Please provide brand, model, and year'
            })

        try:
            year = int(year_str)
        except ValueError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid year format'
            })

        # Find matching car model
        car_model = CarModel.objects.filter(
            brand__name__iexact=brand_name,
            name__iexact=model_name,
            year=year
        ).first()

        if car_model:
            # Find matching tires
            tires = Tire.objects.filter(
                rim_size=car_model.rim_size,
                stock_quantity__gt=0
            )

            return JsonResponse({
                'success': True,
                'rim_size': float(car_model.rim_size),
                'car_model': f"{brand_name} {model_name} {year}",
                'tires_count': tires.count(),
                'tires': list(tires.values(
                    'id', 'brand__name', 'name', 'price',
                    'rim_size', 'width', 'aspect_ratio', 'tire_type', 'stock_quantity'
                ))
            })
        else:
            # Provide helpful error message
            similar_models = CarModel.objects.filter(
                brand__name__iexact=brand_name
            ).values_list('name', flat=True).distinct()

            available_years = CarModel.objects.filter(
                brand__name__iexact=brand_name,
                name__iexact=model_name
            ).values_list('year', flat=True).distinct()

            return JsonResponse({
                'success': False,
                'message': 'Car model not found',
                'available_models': list(similar_models),
                'available_years': list(available_years)
            })

    return JsonResponse({'success': False, 'message': 'Invalid request method'})
