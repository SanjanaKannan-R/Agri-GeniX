"""
SMS and IVR Integration Utilities
Manages SMS notifications and Interactive Voice Response functionality
"""
from django.conf import settings
from django.utils import timezone
from .models import SMSLog, IVRCall, Notification
def is_twilio_configured():
    """Check if Twilio credentials are configured."""
    return all([
        settings.TWILIO_ACCOUNT_SID,
        settings.TWILIO_AUTH_TOKEN,
        settings.TWILIO_PHONE_NUMBER
    ])
def send_sms(user, phone, message):
    """Send SMS notification."""
    return send_sms_notification(user, phone, message)
def create_notification(user, notification_type, title, message, related_booking=None, related_purchase=None):
    """Create a notification for a user."""
    notification = Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        related_booking=related_booking,
        related_purchase=related_purchase
    )
    return notification
def get_user_stats(user):
    """Get user statistics for dashboard."""
    from django.db.models import Count, Avg
    from .models import Review, WarehouseBooking, PurchaseRequest, CropListing
    
    stats = {}
    
    if user.role == "farmer":
        stats['listings'] = CropListing.objects.filter(farmer=user, is_available=True).count()
        stats['bookings'] = WarehouseBooking.objects.filter(farmer=user).count()
        stats['purchase_requests'] = PurchaseRequest.objects.filter(crop__farmer=user).count()
    elif user.role == "buyer":
        stats['purchase_requests'] = PurchaseRequest.objects.filter(buyer=user).count()
        stats['active_requests'] = PurchaseRequest.objects.filter(buyer=user, status='requested').count()
    elif user.role == "warehouse_owner":
        stats['warehouses'] = user.owned_warehouses.count()
        stats['bookings'] = WarehouseBooking.objects.filter(warehouse__owner=user).count()
    review_rating = Review.objects.filter(
        reviewed_user=user
    ).aggregate(avg=Avg('rating'))['avg'] if user.role != "warehouse_owner" else None
    
    stats['average_rating'] = round(review_rating, 2) if review_rating else 0.0
    stats['review_count'] = Review.objects.filter(reviewed_user=user).count() if user.role != "warehouse_owner" else 0
    
    return stats
def generate_ivr_menu():
    """Generate IVR menu options."""
    return {
        1: {"name": "Market Rates", "description": "Check current crop market rates"},
        2: {"name": "Storage Availability", "description": "Find nearby storage solutions"},
        3: {"name": "My Bookings", "description": "Check your storage bookings"},
        4: {"name": "Purchase Requests", "description": "Check purchase requests"},
        0: {"name": "Exit", "description": "End the call"}
    }
