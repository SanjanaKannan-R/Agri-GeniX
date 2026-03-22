"""
Django signals for automatic notification creation
Automatically creates notifications when important events occur
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import (
    PurchaseRequest, 
    WarehouseBooking, 
    Review, 
    Notification,
    CropListing,
    FarmerUser,
)
from .services import send_notification_with_sms


@receiver(post_save, sender=PurchaseRequest)
def create_purchase_notification(sender, instance, created, **kwargs):
    """Create notification when a new purchase request is made."""
    if created:
        farmer = instance.crop.farmer

        notification = send_notification_with_sms(
            farmer,
            'purchase',
            f'New Purchase Request for {instance.crop.crop_name}',
            f'{instance.buyer.get_full_name() or instance.buyer.phone} wants to buy {instance.requested_quantity} {instance.crop.unit} of {instance.crop.crop_name}.',
        )
        notification.related_purchase = instance
        notification.save(update_fields=['related_purchase'])


@receiver(post_save, sender=WarehouseBooking)
def create_booking_notification(sender, instance, created, **kwargs):
    """Create notification when a warehouse booking is confirmed."""
    if created:
        if instance.warehouse.owner:
            notification = send_notification_with_sms(
                instance.warehouse.owner,
                'booking',
                f'New Storage Booking - {instance.crop_name}',
                f'{instance.farmer.get_full_name() or instance.farmer.phone} booked {instance.quantity_tons} tons of storage for {instance.crop_name} from {instance.booking_date}.',
            )
            notification.related_booking = instance
            notification.save(update_fields=['related_booking'])
        notification = send_notification_with_sms(
            instance.farmer,
            'booking',
            f'Booking Confirmed - {instance.warehouse.name_en}',
            f'Your booking for {instance.quantity_tons} tons at {instance.warehouse.name_en} in {instance.warehouse.district} is confirmed for {instance.booking_date}.',
        )
        notification.related_booking = instance
        notification.save(update_fields=['related_booking'])


@receiver(post_save, sender=Review)
def create_review_notification(sender, instance, created, **kwargs):
    """Create notification when a review is left."""
    if created:
        notify_user = instance.reviewed_user

        if notify_user:
            if notify_user.role == "buyer" and instance.reviewer.role != "farmer":
                return

            Notification.objects.create(
                user=notify_user,
                notification_type='review',
                title=f'New {instance.rating}★ Review from {instance.reviewer.get_full_name() or instance.reviewer.phone}',
                message=f'"{instance.title}" - {instance.comment[:100] if instance.comment else "No comment"}',
            )
            if notify_user.phone:
                from .services import send_sms_notification
                sms_text = f'Review: {instance.reviewer.get_full_name() or instance.reviewer.phone} left a {instance.rating}★ review'
                send_sms_notification(notify_user, notify_user.phone, sms_text[:160])


@receiver(post_save, sender=CropListing)
def create_listing_notification(sender, instance, created, **kwargs):
    """Create crop listing notifications for farmer and buyers."""
    if created and instance.is_available:
        Notification.objects.create(
            user=instance.farmer,
            notification_type='system',
            title='Crop Listed Successfully',
            message=f'Your listing for {instance.quantity} {instance.unit} of {instance.crop_name} is now live in the marketplace.',
        )

        buyers = FarmerUser.objects.filter(role="buyer").exclude(id=instance.farmer_id)
        for buyer in buyers:
            send_notification_with_sms(
                buyer,
                "message",
                f"New Farmer Crop: {instance.crop_name}",
                (
                    f"Farmer listing available: {instance.crop_name} ({instance.quantity} {instance.unit}) "
                    f"from {instance.location}."
                ),
            )
