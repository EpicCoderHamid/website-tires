from django import forms
from .models import Order

class CarSearchForm(forms.Form):
    car_brand = forms.CharField(max_length=100, required=True, widget=forms.TextInput(attrs={
        'placeholder': 'Enter car brand ',
        'class': 'form-control'
    }))
    car_model = forms.CharField(max_length=100, required=True, widget=forms.TextInput(attrs={
        'placeholder': 'Enter car model ',
        'class': 'form-control'
    }))
    year = forms.IntegerField(required=True, widget=forms.NumberInput(attrs={
        'placeholder': 'Year',
        'class': 'form-control',
        'min': 1990,
        'max': 2024
    }))


# -------------------------------
# CUSTOMER DETAILS FORM
# -------------------------------
class CustomerDetailsForm(forms.ModelForm):

    apartment_suite = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Apartment, suite, unit (optional)'
        })
    )

    street_address = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter your street address'
        })
    )

    state_province = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'State / Province'
        })
    )

    postal_code = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Postal Code'
        })
    )

    country = forms.CharField(
        max_length=100,
        initial="Pakistan",
        widget=forms.TextInput(attrs={
            'class': 'form-control'
        })
    )

    class Meta:
        model = Order
        fields = [
            'customer_name',
            'customer_email',
            'customer_phone',
            'customer_city',
        ]
        widgets = {
            'customer_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your full name'
            }),
            'customer_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your email'
            }),
            'customer_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Phone number (optional)'
            }),
            'customer_city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City'
            }),
        }


# -------------------------------
# PAYMENT FORM
# -------------------------------
class PaymentForm(forms.Form):
    # Normalized values so view logic can check for 'card', 'paypal', 'cod'
    PAYMENT_METHODS = [
        ('card', 'Debit / Credit Card'),
        ('paypal', 'PayPal'),
        ('cod', 'Cash on Delivery'),
    ]

    payment_method = forms.ChoiceField(
        choices=PAYMENT_METHODS,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label='Payment Method',
        required=True
    )


# -------------------------------
# ORDER SEARCH FORM
# -------------------------------
class OrderSearchForm(forms.Form):
    order_number = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Enter your order number (e.g., ORD123...)',
            'autocomplete': 'off'
        }),
        label='Order Number'
    )
