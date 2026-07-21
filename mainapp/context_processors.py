# mainapp/context_processors.py
from .models import Cart

SESSION_CART_KEY = 'cart_id'

def cart_context(request):
    """
    Provide `cart` in all templates:
      - If authenticated user -> prefer their cart
      - Else -> use session cart id (anonymous)
    """
    cart = None
    try:
        if request.user.is_authenticated:
            cart = Cart.objects.filter(user=request.user).first()
    except Exception:
        cart = None

    # fallback to session cart (anonymous)
    if not cart:
        cart_id = request.session.get(SESSION_CART_KEY)
        if cart_id:
            try:
                cart = Cart.objects.filter(id=cart_id, user__isnull=True).first()
            except Exception:
                cart = None

    return {'cart': cart}
