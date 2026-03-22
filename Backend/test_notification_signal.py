"""Quick test to demonstrate notification signals in action"""
import os
import sys
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agrigenix.settings')
django.setup()
from core.models import (
    Notification, SMSLog, PurchaseRequest, 
    FarmerUser, CropListing
)
def test_notification_signal():
    """Test that creating a purchase request triggers a notification"""
    
    print("\n" + "=" * 70)
    print(" NOTIFICATION SIGNAL LIVE TEST")
    print("=" * 70)
    farmer = FarmerUser.objects.filter(role='farmer').first()
    buyer = FarmerUser.objects.filter(role='buyer').first()
    crop = CropListing.objects.filter(is_available=True).first()
    if not farmer or not buyer or not crop:
        print("\n❌ Missing test data. Please ensure you have:")
        print("   - At least one farmer")
        print("   - At least one buyer")
        print("   - At least one available crop")
        print("\nRun: python manage.py populate_sample_data")
        return False
     print(f"\n📋 Test Setup:")
    print(f"   Buyer: {buyer.username} ({buyer.phone})")
    print(f"   Farmer: {farmer.username} ({farmer.phone})")
    print(f"   Crop: {crop.crop_name} (ID: {crop.id})")
    notif_before = Notification.objects.filter(user=farmer).count()
    sms_before = SMSLog.objects.count()
    
    print(f"\n📊 Before Creating Purchase:")
    print(f"   Notifications for farmer: {notif_before}")
    print(f"   Total SMS logs: {sms_before}")
    print(f"\n🔄 Creating purchase request...")
    purchase = PurchaseRequest.objects.create(
        buyer=buyer,
        crop=crop,
        requested_quantity='50',
        status='pending'
    )
    print(f"   ✅ Purchase request created (ID: {purchase.id})")
    notif_after = Notification.objects.filter(user=farmer).count()
    sms_after = SMSLog.objects.count()
    
    print(f"\n📊 After Creating Purchase:")
    print(f"   Notifications for farmer: {notif_after}")
    print(f"   Total SMS logs: {sms_after}")
    new_notifs = Notification.objects.filter(user=farmer).order_by('-created_at')[:notif_after - notif_before]
    
    print(f"\n📬 New Notifications Created: {notif_after - notif_before}")
    for notif in new_notifs:
        print(f"   - [{notif.notification_type.upper()}] {notif.title}")
        print(f"     Message: {notif.message}")
        print(f"     Timestamp: {notif.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    
    if notif_after > notif_before:
        print("\n✅ SIGNAL WORKING! Notification created automatically!")
    else:
        print("\n❌ SIGNAL NOT WORKING! No notification created.")
        return False
    print(f"\n📱 New SMS Logs Created: {sms_after - sms_before}")
    new_sms = SMSLog.objects.all().order_by('-created_at')[:sms_after - sms_before]
    for sms in new_sms:
        print(f"   - To: {sms.recipient}")
        print(f"     Status: {sms.status}")
        print(f"     Provider: {sms.provider}")
        print(f"     Message: {sms.message[:50]}...")
    
    if sms_after > sms_before:
        print("\n✅ SMS SIGNAL WORKING! SMS logged automatically!")
    else:
        print("\n ℹ️  No SMS created (might need Twilio configuration)")
    
    print("\n" + "=" * 70)
    print(" TEST COMPLETE!")
    print("=" * 70)
    print("\n✅ AUTOMATIC NOTIFICATIONS ARE WORKING!")
    print("\nNext steps:")
    print("1. View notification in admin: /admin/core/notification/")
    print("2. Check SMS log in admin: /admin/core/smslog/")
    print("3. Visit /notifications/ while logged in as farmer")
    print("4. The new notification should appear in the dashboard")
    print("\n")
    
    return True

if __name__ == '__main__':
    success = test_notification_signal()
    sys.exit(0 if success else 1)
