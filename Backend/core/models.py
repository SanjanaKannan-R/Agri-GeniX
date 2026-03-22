from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class FarmerUser(AbstractUser):
    ROLE_CHOICES = (
        ("farmer", "Farmer"),
        ("buyer", "Buyer"),
        ("warehouse_owner", "Warehouse Owner"),
    )

    phone = models.CharField(max_length=20, unique=True, blank=True, null=True)
    preferred_language = models.CharField(max_length=5, default="en")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="farmer")

    def save(self, *args, **kwargs):
        if not self.username:
            base = self.phone or self.email or f"user-{timezone.now().timestamp()}"
            self.username = base.replace("@", "_").replace("+", "").replace(" ", "_")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.get_full_name() or self.phone or self.email or self.username


class OTPRequest(models.Model):
    PURPOSE_CHOICES = (("login", "Login"),)

    user = models.ForeignKey(FarmerUser, on_delete=models.CASCADE, related_name="otp_requests")
    identifier = models.CharField(max_length=255)
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES, default="login")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        return not self.is_used and self.expires_at >= timezone.now()

    def __str__(self):
        return f"{self.identifier} - {self.code}"


class CropListing(models.Model):
    UNIT_CHOICES = (
        ("kg", "Kg"),
        ("quintal", "Quintal"),
        ("ton", "Ton"),
    )

    farmer = models.ForeignKey(FarmerUser, on_delete=models.CASCADE, related_name="crop_listings")
    crop_name = models.CharField(max_length=100)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default="kg")
    location = models.CharField(max_length=120)
    expected_price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="crops/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_available = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.crop_name} - {self.location}"


class Warehouse(models.Model):
    owner = models.ForeignKey(
        FarmerUser,
        on_delete=models.SET_NULL,
        related_name="owned_warehouses",
        null=True,
        blank=True,
        limit_choices_to={"role": "warehouse_owner"},
    )
    name_en = models.CharField(max_length=120)
    name_ta = models.CharField(max_length=120)
    district = models.CharField(max_length=120)
    district_ta = models.CharField(max_length=120, blank=True, default="")
    scheme_name = models.CharField(max_length=120, blank=True, default="")
    warehouse_source = models.CharField(max_length=40, blank=True, default="excel")
    latitude = models.FloatField(default=10.7905)
    longitude = models.FloatField(default=78.7047)
    capacity_tons = models.PositiveIntegerField()
    available_tons = models.PositiveIntegerField()
    contact_number = models.CharField(max_length=20)
    address_text = models.TextField(blank=True, default="")
    sector_name = models.CharField(max_length=120, blank=True, default="")
    commodity_details = models.TextField(blank=True, default="")
    image = models.ImageField(upload_to="warehouses/", blank=True, null=True)

    class Meta:
        ordering = ["district", "name_en"]

    def __str__(self):
        return self.name_en


class WarehouseBooking(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("cancelled", "Cancelled"),
    )

    SLOT_CHOICES = (
        ("morning", "Morning (06:00-10:00)"),
        ("afternoon", "Afternoon (10:00-14:00)"),
        ("evening", "Evening (14:00-18:00)"),
        ("night", "Night (18:00-22:00)"),
    )

    farmer = models.ForeignKey(FarmerUser, on_delete=models.CASCADE, related_name="warehouse_bookings")
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name="bookings")
    crop_name = models.CharField(max_length=100)
    quantity_tons = models.DecimalField(max_digits=8, decimal_places=2)
    booking_date = models.DateField()
    booking_slot = models.CharField(max_length=20, choices=SLOT_CHOICES, default="morning")
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="confirmed")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.crop_name} - {self.warehouse.name_en} ({self.booking_slot})"


class PurchaseRequest(models.Model):
    STATUS_CHOICES = (
        ("requested", "Requested"),
        ("accepted", "Accepted"),
        ("rejected", "Rejected"),
    )

    buyer = models.ForeignKey(FarmerUser, on_delete=models.CASCADE, related_name="purchase_requests")
    crop = models.ForeignKey(CropListing, on_delete=models.CASCADE, related_name="purchase_requests")
    requested_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    message = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="requested")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.buyer} -> {self.crop}"


class Conversation(models.Model):
    buyer = models.ForeignKey(FarmerUser, on_delete=models.CASCADE, related_name="buyer_conversations")
    farmer = models.ForeignKey(FarmerUser, on_delete=models.CASCADE, related_name="farmer_conversations")
    crop = models.ForeignKey(CropListing, on_delete=models.SET_NULL, null=True, blank=True, related_name="conversations")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        unique_together = ("buyer", "farmer", "crop")

    def __str__(self):
        crop_name = self.crop.crop_name if self.crop else "General"
        return f"{self.buyer} <-> {self.farmer} ({crop_name})"


class ChatMessage(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(FarmerUser, on_delete=models.CASCADE, related_name="sent_messages")
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender} -> {self.conversation_id}"


class Review(models.Model):
    TYPE_CHOICES = (
        ("farmer", "Farmer"),
        ("buyer", "Buyer"),
        ("warehouse", "Warehouse"),
    )

    reviewer = models.ForeignKey(FarmerUser, on_delete=models.CASCADE, related_name="reviews_given")
    reviewed_user = models.ForeignKey(FarmerUser, on_delete=models.CASCADE, related_name="reviews_received", blank=True, null=True)
    reviewed_warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name="reviews", blank=True, null=True)
    rating = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    title = models.CharField(max_length=200)
    comment = models.TextField(blank=True)
    review_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("reviewer", "reviewed_user", "reviewed_warehouse")

    def __str__(self):
        return f"{self.reviewer} -> {self.reviewed_user or self.reviewed_warehouse} ({self.rating}★)"


class Notification(models.Model):
    TYPE_CHOICES = (
        ("booking", "Booking"),
        ("purchase", "Purchase"),
        ("review", "Review"),
        ("message", "Message"),
        ("system", "System"),
    )

    user = models.ForeignKey(FarmerUser, on_delete=models.CASCADE, related_name="notifications")
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    related_booking = models.ForeignKey(WarehouseBooking, on_delete=models.SET_NULL, null=True, blank=True)
    related_purchase = models.ForeignKey(PurchaseRequest, on_delete=models.SET_NULL, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    is_sent_sms = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} - {self.user}"


class SMSLog(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("sent", "Sent"),
        ("failed", "Failed"),
    )

    user = models.ForeignKey(FarmerUser, on_delete=models.CASCADE, related_name="sms_logs")
    phone = models.CharField(max_length=20)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    external_id = models.CharField(max_length=255, blank=True, null=True)
    error_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"SMS to {self.phone} - {self.status}"


class IVRCall(models.Model):
    STATUS_CHOICES = (
        ("initiated", "Initiated"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    )

    user = models.ForeignKey(FarmerUser, on_delete=models.CASCADE, related_name="ivr_calls")
    phone = models.CharField(max_length=20)
    call_id = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="initiated")
    duration_seconds = models.IntegerField(default=0)
    transcript = models.TextField(blank=True)
    action_taken = models.CharField(max_length=255, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"IVR Call {self.call_id} - {self.status}"
