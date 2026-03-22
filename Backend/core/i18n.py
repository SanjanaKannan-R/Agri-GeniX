STRINGS = {
    "brand_name": {"en": "Agri Genix", "ta": "Agri Genix"},
    "tagline": {
        "en": "Professional tools for market access, storage planning, and secure sign-in.",
        "ta": "Professional tools for market access, storage planning, and secure sign-in.",
    },
    "hero_title": {
        "en": "Simple agricultural operations in one place",
        "ta": "Simple agricultural operations in one place",
    },
    "hero_body": {
        "en": "Manage crops, compare market prices, find storage, and handle sign-in from one connected platform.",
        "ta": "Manage crops, compare market prices, find storage, and handle sign-in from one connected platform.",
    },
    "login": {"en": "Login", "ta": "Login"},
    "logout": {"en": "Logout", "ta": "Logout"},
    "dashboard": {"en": "Dashboard", "ta": "Dashboard"},
    "marketplace": {"en": "Marketplace", "ta": "Marketplace"},
    "storage": {"en": "Storage", "ta": "Storage"},
    "add_crop": {"en": "Add Crop", "ta": "Add Crop"},
    "language": {"en": "Language", "ta": "Language"},
    "otp_title": {"en": "OTP Login", "ta": "OTP Login"},
    "otp_body": {
        "en": "Use your phone number or email to receive a one-time password.",
        "ta": "Use your phone number or email to receive a one-time password.",
    },
    "request_otp": {"en": "Send OTP", "ta": "Send OTP"},
    "verify_otp": {"en": "Verify OTP", "ta": "Verify OTP"},
    "your_crops": {"en": "Your Crop Listings", "ta": "Your Crop Listings"},
    "nearby_storage": {"en": "Nearby Warehouses", "ta": "Nearby Warehouses"},
    "buyer_market": {"en": "Buyer Marketplace", "ta": "Buyer Marketplace"},
    "welcome": {"en": "Welcome", "ta": "Welcome"},
    "simple_ui_note": {
        "en": "Clear text and consistent layouts across every page.",
        "ta": "Clear text and consistent layouts across every page.",
    },
}


def get_language(request):
    lang = request.session.get("language", "en")
    return lang if lang in {"en", "ta"} else "en"


def get_ui(lang):
    return {key: values.get(lang, values["en"]) for key, values in STRINGS.items()}
