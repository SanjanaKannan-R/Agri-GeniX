from django import forms
from .models import CropListing, PurchaseRequest, Warehouse, WarehouseBooking, Review, Notification
class OTPRequestForm(forms.Form):
    identifier = forms.CharField(
        label="Phone or Email",
        max_length=255,
        widget=forms.TextInput(attrs={"placeholder": "Enter your phone number or email"}),
    )
    role = forms.ChoiceField(
        choices=(
            ("farmer", "Farmer"),
            ("buyer", "Buyer"),
            ("warehouse_owner", "Warehouse Owner"),
        ),
        initial="farmer",
        widget=forms.HiddenInput(),
    )
class OTPVerifyForm(forms.Form):
    identifier = forms.CharField(widget=forms.HiddenInput())
    role = forms.CharField(widget=forms.HiddenInput(), required=False)
    code = forms.CharField(
        label="OTP",
        max_length=6,
        widget=forms.TextInput(attrs={"placeholder": "Enter 6-digit OTP"}),
    )
class CropListingForm(forms.ModelForm):
    class Meta:
        model = CropListing
        fields = ["crop_name", "quantity", "unit", "location", "expected_price", "description", "image"]
        widgets = {
            "crop_name": forms.TextInput(attrs={"placeholder": "Paddy, Tomato, Groundnut"}),
            "location": forms.TextInput(attrs={"placeholder": "Village / District"}),
            "description": forms.Textarea(attrs={"rows": 4, "placeholder": "Optional notes"}),
            "image": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }
class WarehouseBookingForm(forms.ModelForm):
    class Meta:
        model = WarehouseBooking
        fields = ["crop_name", "quantity_tons", "booking_date", "booking_slot", "notes"]
        widgets = {
            "crop_name": forms.TextInput(attrs={"placeholder": "Paddy, Tomato, Groundnut"}),
            "booking_date": forms.DateInput(attrs={"type": "date"}),
            "booking_slot": forms.Select(),
            "notes": forms.Textarea(attrs={"rows": 3, "placeholder": "Optional notes"}),
        }
class PurchaseRequestForm(forms.ModelForm):
    class Meta:
        model = PurchaseRequest
        fields = ["requested_quantity", "message"]
        widgets = {
            "message": forms.Textarea(attrs={"rows": 3, "placeholder": "Share your buying request"}),
        }
class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = [
            "name_en",
            "name_ta",
            "district",
            "district_ta",
            "scheme_name",
            "latitude",
            "longitude",
            "capacity_tons",
            "available_tons",
            "contact_number",
            "image",
        ]

        widgets = {
            "image": forms.ClearableFileInput(attrs={"accept": "image/*"}),
        }


def localize_form(form, language):
    if language == "ta":
        localized = {
            "identifier": ("\u0ba4\u0bca\u0bb2\u0bc8\u0baa\u0bc7\u0b9a\u0bbf \u0b8e\u0ba3\u0bcd \u0b85\u0bb2\u0bcd\u0bb2\u0ba4\u0bc1 \u0bae\u0bbf\u0ba9\u0bcd\u0ba9\u0b9e\u0bcd\u0b9a\u0bb2\u0bcd", "\u0b89\u0b99\u0bcd\u0b95\u0bb3\u0bcd \u0ba4\u0bca\u0bb2\u0bc8\u0baa\u0bc7\u0b9a\u0bbf \u0b8e\u0ba3\u0bcd \u0b85\u0bb2\u0bcd\u0bb2\u0ba4\u0bc1 \u0bae\u0bbf\u0ba9\u0bcd\u0ba9\u0b9e\u0bcd\u0b9a\u0bb2\u0bc8 \u0b89\u0bb3\u0bcd\u0bb3\u0bbf\u0b9f\u0bb5\u0bc1\u0bae\u0bcd"),
            "role": ("\u0baa\u0baf\u0ba9\u0bb0\u0bcd \u0bb5\u0b95\u0bc8", None),
            "code": ("OTP", "6 \u0b87\u0bb2\u0b95\u0bcd\u0b95 OTP \u0b90 \u0b89\u0bb3\u0bcd\u0bb3\u0bbf\u0b9f\u0bb5\u0bc1\u0bae\u0bcd"),
            "crop_name": ("\u0baa\u0baf\u0bbf\u0bb0\u0bcd \u0baa\u0bc6\u0baf\u0bb0\u0bcd", "\u0ba8\u0bc6\u0bb2\u0bcd, \u0ba4\u0b95\u0bcd\u0b95\u0bbe\u0bb3\u0bbf, \u0ba8\u0bbf\u0bb2\u0b95\u0bcd\u0b95\u0b9f\u0bb2\u0bc8"),
            "quantity": ("\u0b85\u0bb3\u0bb5\u0bc1", None),
            "unit": ("\u0b85\u0bb2\u0b95\u0bc1", None),
            "location": ("\u0b87\u0b9f\u0bae\u0bcd", "\u0b95\u0bbf\u0bb0\u0bbe\u0bae\u0bae\u0bcd / \u0bae\u0bbe\u0bb5\u0b9f\u0bcd\u0b9f\u0bae\u0bcd"),
            "expected_price": ("\u0b8e\u0ba4\u0bbf\u0bb0\u0bcd\u0baa\u0bbe\u0bb0\u0bcd\u0b95\u0bcd\u0b95\u0bc1\u0bae\u0bcd \u0bb5\u0bbf\u0bb2\u0bc8", None),
            "description": ("\u0b95\u0bc1\u0bb1\u0bbf\u0baa\u0bcd\u0baa\u0bc1", "\u0bb5\u0bbf\u0bb0\u0bc1\u0baa\u0bcd\u0baa \u0b95\u0bc1\u0bb1\u0bbf\u0baa\u0bcd\u0baa\u0bc1"),
            "image": ("\u0baa\u0b9f\u0bae\u0bcd", None),
            "quantity_tons": ("\u0b9f\u0ba9\u0bcd \u0b85\u0bb3\u0bb5\u0bc1", None),
            "booking_date": ("\u0baa\u0ba4\u0bbf\u0bb5\u0bc1 \u0ba4\u0bc7\u0ba4\u0bbf", None),
            "booking_slot": ("\u0b95\u0bbe\u0bb2 \u0b87\u0b9f\u0bc8\u0bb5\u0bc6\u0bb3\u0bbf", None),
            "notes": ("\u0b95\u0bbf\u0b9f\u0b99\u0bcd\u0b95\u0bc1 \u0b95\u0bc1\u0bb1\u0bbf\u0baa\u0bcd\u0baa\u0bc1", "\u0bb5\u0bbf\u0bb0\u0bc1\u0baa\u0bcd\u0baa \u0b95\u0bc1\u0bb1\u0bbf\u0baa\u0bcd\u0baa\u0bc1"),
            "requested_quantity": ("\u0bb5\u0bbe\u0b99\u0bcd\u0b95 \u0bb5\u0bc7\u0ba3\u0bcd\u0b9f\u0bbf\u0baf \u0b85\u0bb3\u0bb5\u0bc1", None),
            "message": ("\u0bb5\u0bbe\u0b99\u0bcd\u0b95\u0bc1\u0baa\u0bb5\u0bb0\u0bcd \u0b95\u0bc1\u0bb1\u0bbf\u0baa\u0bcd\u0baa\u0bc1", "\u0b89\u0b99\u0bcd\u0b95\u0bb3\u0bcd \u0ba4\u0bc7\u0bb5\u0bc8\u0baf\u0bc8 \u0b8e\u0bb4\u0bc1\u0ba4\u0bc1\u0b99\u0bcd\u0b95\u0bb3\u0bcd"),
            "name_en": ("Warehouse Name (English)", None),
            "name_ta": ("\u0b95\u0bbf\u0b9f\u0b99\u0bcd\u0b95\u0bc1 \u0baa\u0bc6\u0baf\u0bb0\u0bcd", None),
            "district": ("\u0bae\u0bbe\u0bb5\u0b9f\u0bcd\u0b9f\u0bae\u0bcd", None),
            "district_ta": ("\u0bae\u0bbe\u0bb5\u0b9f\u0bcd\u0b9f\u0bae\u0bcd (\u0ba4\u0bae\u0bbf\u0bb4\u0bcd)", None),
            "scheme_name": ("\u0ba4\u0bbf\u0b9f\u0bcd\u0b9f\u0bae\u0bcd / \u0bb5\u0b95\u0bc8", None),
            "latitude": ("\u0b85\u0b9f\u0bcd\u0b9a\u0bb0\u0bc7\u0b95\u0bc8", None),
            "longitude": ("\u0ba4\u0bc0\u0bb0\u0bcd\u0b95\u0bcd\u0b95\u0bb0\u0bc7\u0b95\u0bc8", None),
            "capacity_tons": ("\u0bae\u0bca\u0ba4\u0bcd\u0ba4 \u0b95\u0bca\u0bb3\u0bcd\u0bb3\u0bb3\u0bb5\u0bc1", None),
            "available_tons": ("\u0b95\u0bbe\u0bb2\u0bbf \u0b87\u0b9f\u0bae\u0bcd", None),
            "contact_number": ("\u0ba4\u0bca\u0b9f\u0bb0\u0bcd\u0baa\u0bc1 \u0b8e\u0ba3\u0bcd", None),
        }
    else:
        localized = {
            "identifier": ("Phone or Email", "Enter your phone number or email"),
            "role": ("User Type", None),
            "code": ("OTP", "Enter 6-digit OTP"),
            "crop_name": ("Crop Name", "Paddy, Tomato, Groundnut"),
            "quantity": ("Quantity", None),
            "unit": ("Unit", None),
            "location": ("Location", "Village / District"),
            "expected_price": ("Expected Price", None),
            "description": ("Notes", "Optional notes"),
            "image": ("Photo", None),
            "quantity_tons": ("Quantity in Tons", None),
            "booking_date": ("Booking Date", None),
            "booking_slot": ("Booking Slot", None),
            "notes": ("Storage Notes", "Optional notes"),
            "requested_quantity": ("Required Quantity", None),
            "message": ("Buyer Message", "Share your buying request"),
            "name_en": ("Warehouse Name (English)", None),
            "name_ta": ("Warehouse Name (Tamil)", None),
            "district": ("District", None),
            "district_ta": ("District (Tamil)", None),
            "scheme_name": ("Scheme / Type", "NADP, Private Warehouse, Govt Storage"),
            "latitude": ("Latitude", None),
            "longitude": ("Longitude", None),
            "capacity_tons": ("Total Capacity", None),
            "available_tons": ("Available Capacity", None),
            "contact_number": ("Contact Number", None),
        }

    for field_name, (label, placeholder) in localized.items():
        if field_name in form.fields:
            form.fields[field_name].label = label
            if placeholder and hasattr(form.fields[field_name].widget, "attrs"):
                form.fields[field_name].widget.attrs["placeholder"] = placeholder
    return form


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ["rating", "title", "comment"]
        widgets = {
            "rating": forms.RadioSelect(choices=[(i, f"{i}★") for i in range(1, 6)]),
            "title": forms.TextInput(attrs={"placeholder": "Brief review title"}),
            "comment": forms.Textarea(attrs={"rows": 4, "placeholder": "Your detailed review (optional)"}),
        }
class MarketplaceFilterForm(forms.Form):
    SORT_CHOICES = [
        ("newest", "Newest"),
        ("price_low", "Price: Low to High"),
        ("price_high", "Price: High to Low"),
        ("distance", "Nearest"),
    ]

    search_query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Search crops..."}),
    )
    min_price = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={"placeholder": "Min price"}),
    )
    max_price = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={"placeholder": "Max price"}),
    )
    location = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Location/District"}),
    )
    unit = forms.ChoiceField(
        required=False,
        choices=[("", "All Units"), ("kg", "Kg"), ("quintal", "Quintal"), ("ton", "Ton")],
    )
    sort_by = forms.ChoiceField(
        required=False,
        choices=SORT_CHOICES,
        initial="newest",
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
