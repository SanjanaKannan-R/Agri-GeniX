
"""Quick verification script for notification system"""

import os
import sys
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'agrigenix.settings')
django.setup()

from core.models import (
    Notification, SMSLog, PurchaseRequest, 
    WarehouseBooking, Review, FarmerUser, CropListing
)
from django.db.models import Count

def separator(title=""):
    if title:
        print(f"\n{'=' * 60}")
        print(f" {title}")
        print(f"{'=' * 60}\n")
    else:
        print(f"{'=' * 60}\n")

def check_signals():
    """Verify signals are registered"""
    print("📡 CHECKING SIGNAL REGISTRATION...")
    try:
        import core.signals
        print("✅ core.signals module imported successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to import signals: {e}")
        return False

def check_notifications():
    """Check existing notifications"""
    separator("NOTIFICATIONS")
    
    total = Notification.objects.count()
    print(f"📬 Total Notifications: {total}")
    
    notif_counts = Notification.objects.values('notification_type').annotate(count=Count('id')).order_by('-count')
    for item in notif_counts:
        notification_type = item['notification_type'].upper()
        count = item['count']
        print(f"   ├─ {notification_type}: {count}")
    
    unread = Notification.objects.filter(is_read=False).count()
    print(f"\n🔔 Unread Notifications: {unread}")
    
    if total == 0:
        print("\n⚠️  No notifications yet. Create some test data to see notifications in action.")
    else:
        print(f"\n✅ Notification System Active ({total} records)")
    
    return total

def check_sms():
    """Check SMS logs"""
    separator("SMS LOGS")
    
    total = SMSLog.objects.count()
    print(f"📱 Total SMS Logs: {total}")
    
    sms_counts = SMSLog.objects.values('status').annotate(count=Count('id')).order_by('-count')
    for item in sms_counts:
        status = item['status'].upper()
        count = item['count']
        providers = SMSLog.objects.filter(status=status.lower()).values('provider').annotate(count=Count('id'))
        provider_str = ", ".join([f"{p['provider']}: {p['count']}" for p in providers])
        print(f"   ├─ {status}: {count} ({provider_str})")
    
    if total == 0:
        print("\n⚠️  No SMS logs yet. SMS will be logged when notifications are created.")
    else:
        print(f"\n✅ SMS System Active ({total} logs)")
    
    return total

def check_models():
    """Check if required models have data"""
    separator("MODEL DATA")
    
    farmers = FarmerUser.objects.filter(role='farmer').count()
    buyers = FarmerUser.objects.filter(role='buyer').count()
    owners = FarmerUser.objects.filter(role='warehouse_owner').count()
    crops = CropListing.objects.count()
    purchases = PurchaseRequest.objects.count()
    bookings = WarehouseBooking.objects.count()
    reviews = Review.objects.count()
    
    print(f"👥 Users:")
    print(f"   ├─ Farmers: {farmers}")
    print(f"   ├─ Buyers: {buyers}")
    print(f"   └─ Warehouse Owners: {owners}")
    
    print(f"\n🌾 Data:")
    print(f"   ├─ Crop Listings: {crops}")
    print(f"   ├─ Purchase Requests: {purchases}")
    print(f"   ├─ Warehouse Bookings: {bookings}")
    print(f"   └─ Reviews: {reviews}")
    
    return {
        'farmers': farmers,
        'buyers': buyers,
        'owners': owners,
        'crops': crops,
        'purchases': purchases,
        'bookings': bookings,
        'reviews': reviews
    }

def check_admin_access():
    """Check admin configuration"""
    separator("ADMIN INTERFACE")
    
    from django.contrib.admin import site
    
    registered = [model._meta.label_lower for model, admin in site._registry.items()]
    
    required_models = [
        'core.notification',
        'core.smslog',
        'core.purchaserequest',
        'core.warehousebooking',
        'core.review'
    ]
    
    all_registered = True
    for model in required_models:
        if model in registered:
            print(f"✅ {model.upper()} - Admin registered")
        else:
            print(f"❌ {model.upper()} - NOT registered")
            all_registered = False
    
    if all_registered:
        print("\n✅ All models available in admin at /admin/")
    else:
        print("\n⚠️  Some models missing from admin registration")
    
    return all_registered

def check_views():
    """Check if views are accessible"""
    separator("VIEW ROUTES")
    
    from django.urls import get_resolver
    from django.urls.exceptions import Resolver404
    
    required_views = [
        ('notifications', 'notifications'),
        ('market-dashboard', 'market_data_dashboard'),
        ('marketplace', 'marketplace')
    ]
    
    resolver = get_resolver()
    all_available = True
    
    for view_name, description in required_views:
        try:
            url = resolver.reverse(view_name)
            print(f"✅ {description.upper()} - {url}")
        except Resolver404:
            print(f"❌ {description.upper()} - NOT found")
            all_available = False
    
    if all_available:
        print("\n✅ All critical views configured and accessible")
    else:
        print("\n⚠️  Some views missing from URL configuration")
    
    return all_available

def main():
    """Run all checks"""
    print("\n")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║   AGRI GENIX - NOTIFICATION SYSTEM VERIFICATION            ║")
    print("╚════════════════════════════════════════════════════════════╝")
    
    signals_ok = check_signals()
    notif_count = check_notifications()
    sms_count = check_sms()
    models_data = check_models()
    admin_ok = check_admin_access()
    views_ok = check_views()
    
    separator("SYSTEM STATUS")
    
    checks = {
        'Signal Registration': signals_ok,
        'Admin Interface': admin_ok,
        'View Routes': views_ok,
        'Notification Data': notif_count > 0,
        'SMS Logging': sms_count > 0
    }
    
    passed = sum(1 for v in checks.values() if v)
    total = len(checks)
    
    for check_name, status in checks.items():
        symbol = "✅" if status else "⚠️ "
        print(f"{symbol} {check_name}")
    
    print(f"\nStatus: {passed}/{total} checks passed")
    
    if signals_ok and admin_ok and views_ok:
        print("\n" + "=" * 60)
        print("🎉 NOTIFICATION SYSTEM IS READY!")
        print("=" * 60)
        print("\nNext Steps:")
        print("1. Start server: python manage.py runserver")
        print("2. Create test data (farmers, buyers, crops)")
        print("3. Make purchase offers to trigger notifications")
        print("4. View notifications at /notifications/")
        print("5. Check SMS logs at /admin/core/smslog/")
        print("\nFor detailed instructions, see: TESTING_NOTIFICATIONS.md")
    else:
        print("\n⚠️  Some checks failed. Review the output above.")
    
    print("\n")

if __name__ == '__main__':
    main()
