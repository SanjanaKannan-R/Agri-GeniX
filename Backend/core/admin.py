from django.contrib import admin
from .models import CropListing, FarmerUser, OTPRequest, PurchaseRequest, Warehouse, WarehouseBooking, Review, Notification, SMSLog, IVRCall
@admin.register(FarmerUser)
class FarmerUserAdmin(admin.ModelAdmin):
    list_display = ("username", "phone", "email", "role", "preferred_language")
    search_fields = ("username", "phone", "email")


@admin.register(CropListing)
class CropListingAdmin(admin.ModelAdmin):
    list_display = ("crop_name", "farmer", "quantity", "unit", "location", "expected_price", "is_available", "image")
    list_filter = ("is_available", "unit")
    search_fields = ("crop_name", "location", "farmer__username")


@admin.register(OTPRequest)
class OTPRequestAdmin(admin.ModelAdmin):
    list_display = ("identifier", "code", "created_at", "expires_at", "is_used")
    list_filter = ("is_used",)
    search_fields = ("identifier", "user__username")


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("name_en", "owner", "district", "capacity_tons", "available_tons", "contact_number", "image")
    search_fields = ("name_en", "name_ta", "district")


@admin.register(WarehouseBooking)
class WarehouseBookingAdmin(admin.ModelAdmin):
    list_display = ("farmer", "warehouse", "crop_name", "quantity_tons", "booking_date", "booking_slot", "status")
    list_filter = ("status", "booking_date", "booking_slot")
    search_fields = ("farmer__username", "warehouse__name_en", "crop_name")


@admin.register(PurchaseRequest)
class PurchaseRequestAdmin(admin.ModelAdmin):
    list_display = ("buyer", "crop", "requested_quantity", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("buyer__username", "crop__crop_name")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("reviewer", "rating", "review_type", "created_at")
    list_filter = ("rating", "review_type", "created_at")
    search_fields = ("reviewer__username", "title", "comment")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "notification_type", "title", "is_read", "is_sent_sms", "created_at")
    list_filter = ("notification_type", "is_read", "is_sent_sms", "created_at")
    search_fields = ("user__username", "title", "message")
    readonly_fields = ("created_at",)


@admin.register(SMSLog)
class SMSLogAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "status", "sent_at", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("user__username", "phone", "message")
    readonly_fields = ("created_at", "sent_at", "external_id")


@admin.register(IVRCall)
class IVRCallAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "call_id", "status", "duration_seconds", "started_at")
    list_filter = ("status", "started_at")
    search_fields = ("user__username", "phone", "call_id")
    readonly_fields = ("started_at", "ended_at")
