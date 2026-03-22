import json
from django.contrib import messages
from decimal import Decimal
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.db.models import Q, Avg, Sum
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from .forms import (
    CropListingForm,
    OTPRequestForm,
    OTPVerifyForm,
    PurchaseRequestForm,
    WarehouseBookingForm,
    WarehouseForm,
    ReviewForm,
    MarketplaceFilterForm,
    localize_form,
)
from .i18n import get_language, get_ui
from .models import CropListing, OTPRequest, PurchaseRequest, Warehouse, WarehouseBooking, Review, Notification
from .services import (
    WAREHOUSE_DEFAULT_IMAGE,
    create_otp,
    crop_image,
    crop_hint,
    dispatch_otp,
    get_realtime_market_data,
    get_realtime_storage_data,
    haversine_km,
    initiate_ivr_call,
    load_market_rate_rows,
    normalize_identifier,
    normalize_search_query,
    price_band,
    resolve_user,
    seed_warehouses,
    send_notification_with_sms,
    calculate_user_rating,
    get_warehouse_rating,
)
ROLE_META = {
    "farmer": {
        "title": "Farmer Portal",
        "eyebrow": "Farmer",
        "description": "Add crop listings, track bookings, and find nearby storage.",
        "dashboard_url_name": "farmer-portal",
    },
    "buyer": {
        "title": "Buyer Portal",
        "eyebrow": "Buyer",
        "description": "Browse live crop listings, compare locations, and connect with farmers.",
        "dashboard_url_name": "buyer-portal",
    },
    "warehouse_owner": {
        "title": "Warehouse Owner Portal",
        "eyebrow": "Warehouse",
        "description": "View warehouse capacity, monitor bookings, and manage storage operations.",
        "dashboard_url_name": "warehouse-portal",
    },
}


def get_role_meta(role):
    meta = ROLE_META.get(role)
    if not meta:
        raise Http404("Unknown portal role.")
    return meta


def get_dashboard_url_for_role(role):
    return reverse(get_role_meta(role)["dashboard_url_name"])


def build_context(request, **kwargs):
    language = get_language(request)
    portal_home = kwargs.pop("portal_home", None)
    context = {
        "language_code": language,
        "ui": get_ui(language),
        "portal_home": portal_home or (
            get_dashboard_url_for_role(request.user.role) if getattr(request.user, "is_authenticated", False) else reverse("portal-home")
        ),
    }
    context.update(kwargs)
    return context


def crop_image_url(crop):
    if getattr(crop, "image", None):
        try:
            return crop.image.url
        except ValueError:
            pass
    return crop_image(crop.crop_name)


def warehouse_image_url(warehouse):
    if getattr(warehouse, "image", None):
        try:
            return warehouse.image.url
        except ValueError:
            pass
    return WAREHOUSE_DEFAULT_IMAGE


def buyer_visible_crop_listings():
    queryset = CropListing.objects.filter(is_available=True).select_related("farmer")
    demo_filters = (
        Q(crop_name__iregex=r"\b(?:demo|test|sample|smoke)\b")
        | Q(location__iregex=r"\b(?:demo|test|sample|smoke)\b")
        | Q(description__iregex=r"\b(?:demo|test|sample|smoke)\b")
        | Q(farmer__username__iregex=r"(?:demo|test|sample|smoke)")
        | Q(farmer__email__iregex=r"(?:demo|test|sample|smoke)")
    )
    return queryset.exclude(demo_filters)




def home(request):
    return redirect("portal-home")


def offline_page(request):
    return render(request, "core/offline.html", build_context(request))


def service_worker(request):
    script = """
const CACHE_NAME = "agrigenix-pwa-v1";
const OFFLINE_URL = "/offline/";
const CORE_ASSETS = [
  "/login/",
  "/offline/",
  "/static/core/styles.css",
  "/static/core/app.js",
  "/static/core/images/agrigenix-logo.svg",
  "/static/manifest.webmanifest"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(CORE_ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        const copy = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
        return response;
      })
      .catch(() =>
        caches.match(event.request).then((cached) => cached || caches.match(OFFLINE_URL))
      )
  );
});
"""
    return HttpResponse(script, content_type="application/javascript")


def portal_home(request):
    portals = []
    for role, meta in ROLE_META.items():
        portals.append(
            {
                "role": role,
                "title": meta["title"],
                "eyebrow": meta["eyebrow"],
                "description": meta["description"],
                "login_url": (
                    get_dashboard_url_for_role(role)
                    if request.user.is_authenticated and request.user.role == role
                    else reverse("role-login", args=[role])
                ),
            }
        )
    return render(request, "core/portal_home.html", build_context(request, portals=portals))


def request_otp(request, role=None):
    if request.user.is_authenticated:
        return redirect(get_dashboard_url_for_role(request.user.role))

    selected_role = role or request.GET.get("role") or "farmer"
    role_meta = get_role_meta(selected_role)

    initial = {"role": selected_role}
    form = OTPRequestForm(request.POST or None, initial=initial)
    if selected_role in dict(form.fields["role"].choices):
        form.fields["role"].widget.attrs["class"] = "visually-hidden-input"
    localize_form(form, get_language(request))

    if request.method == "POST" and form.is_valid():
        identifier = form.cleaned_data["identifier"]
        role_value = form.cleaned_data["role"]
        user, normalized = resolve_user(identifier, role_value)
        otp = create_otp(user, normalized)
        dispatch_otp(request, normalized, otp.code)
        verify_url = f"{reverse('verify-otp')}?identifier={normalized}&role={role_value}"
        return redirect(verify_url)

    return render(
        request,
        "core/request_otp.html",
        build_context(request, form=form, role_meta=role_meta, selected_role=selected_role, portal_home=reverse("portal-home")),
    )


@csrf_exempt
def api_request_otp(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required"}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        payload = request.POST

    identifier = (payload.get("identifier") or "").strip()
    role = (payload.get("role") or "farmer").strip()
    if not identifier:
        return JsonResponse({"ok": False, "error": "Identifier is required"}, status=400)
    if role not in ROLE_META:
        return JsonResponse({"ok": False, "error": "Invalid role"}, status=400)

    user, normalized = resolve_user(identifier, role)
    otp = create_otp(user, normalized)
    dispatch_otp(request, normalized, otp.code)

    data = {
        "ok": True,
        "identifier": normalized,
        "role": role,
        "expires_in_minutes": settings.OTP_EXPIRY_MINUTES,
        "message": "OTP sent successfully.",
    }
    if settings.SMS_PROVIDER != "twilio":
        data["demo_otp"] = otp.code
    return JsonResponse(data)


def verify_otp(request):
    if request.user.is_authenticated:
        return redirect(get_dashboard_url_for_role(request.user.role))

    initial_identifier = request.GET.get("identifier", "")
    initial_role = request.GET.get("role", "farmer")
    get_role_meta(initial_role)

    form = OTPVerifyForm(request.POST or None, initial={"identifier": initial_identifier, "role": initial_role})
    localize_form(form, get_language(request))
    if request.method == "POST" and form.is_valid():
        identifier = normalize_identifier(form.cleaned_data["identifier"])
        code = form.cleaned_data["code"]
        otp = (
            OTPRequest.objects.select_related("user")
            .filter(identifier=identifier, code=code, is_used=False, expires_at__gte=timezone.now())
            .order_by("-created_at")
            .first()
        )
        if otp and otp.is_valid():
            otp.is_used = True
            otp.save(update_fields=["is_used"])
            login(request, otp.user, backend="django.contrib.auth.backends.ModelBackend")
            request.user.preferred_language = get_language(request)
            request.user.save(update_fields=["preferred_language"])
            messages.success(request, "Login successful.")
            return redirect(get_dashboard_url_for_role(request.user.role))
        messages.error(request, "Invalid or expired OTP. Please try again.")

    return render(
        request,
        "core/verify_otp.html",
        build_context(
            request,
            form=form,
            identifier=initial_identifier,
            role_meta=get_role_meta(initial_role),
            selected_role=initial_role,
            portal_home=reverse("portal-home"),
        ),
    )


@csrf_exempt
def api_verify_otp(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "POST required"}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        payload = request.POST

    identifier = normalize_identifier((payload.get("identifier") or "").strip())
    code = (payload.get("code") or "").strip()
    if not identifier or not code:
        return JsonResponse({"ok": False, "error": "Identifier and code are required"}, status=400)

    otp = (
        OTPRequest.objects.select_related("user")
        .filter(identifier=identifier, code=code, is_used=False, expires_at__gte=timezone.now())
        .order_by("-created_at")
        .first()
    )
    if not otp or not otp.is_valid():
        return JsonResponse({"ok": False, "error": "Invalid or expired OTP"}, status=400)

    otp.is_used = True
    otp.save(update_fields=["is_used"])
    login(request, otp.user, backend="django.contrib.auth.backends.ModelBackend")

    return JsonResponse(
        {
            "ok": True,
            "message": "Login successful.",
            "user": {
                "id": otp.user.id,
                "role": otp.user.role,
                "phone": otp.user.phone,
                "email": otp.user.email,
                "preferred_language": otp.user.preferred_language,
            },
            "redirect_url": get_dashboard_url_for_role(otp.user.role),
        }
    )


@login_required
def dashboard(request):
    return redirect(get_dashboard_url_for_role(request.user.role))


@login_required
def farmer_portal(request):
    if request.user.role != "farmer":
        return redirect(get_dashboard_url_for_role(request.user.role))

    seed_warehouses()
    listings_count = request.user.crop_listings.count()
    bookings_count = request.user.warehouse_bookings.count()
    buyer_requests_count = PurchaseRequest.objects.filter(crop__farmer=request.user).count()
    recent_notifications = request.user.notifications.all()[:5]
    return render(
        request,
        "core/farmer_portal.html",
        build_context(
            request,
            listings_count=listings_count,
            bookings_count=bookings_count,
            buyer_requests_count=buyer_requests_count,
            recent_notifications=recent_notifications,
        ),
    )


@login_required
def buyer_portal(request):
    if request.user.role != "buyer":
        return redirect(get_dashboard_url_for_role(request.user.role))

    seed_warehouses()
    active_crops_count = buyer_visible_crop_listings().count()
    purchase_count = request.user.purchase_requests.count()
    nearby_warehouses_count = Warehouse.objects.count()
    return render(
        request,
        "core/buyer_portal.html",
        build_context(
            request,
            active_crops_count=active_crops_count,
            purchase_count=purchase_count,
            nearby_warehouses_count=nearby_warehouses_count,
        ),
    )


@login_required
def warehouse_portal(request):
    if request.user.role != "warehouse_owner":
        return redirect(get_dashboard_url_for_role(request.user.role))

    seed_warehouses()
    warehouses_count = Warehouse.objects.filter(owner=request.user).count()
    bookings_count = WarehouseBooking.objects.filter(warehouse__owner=request.user).count()
    available_capacity = Warehouse.objects.filter(owner=request.user).values_list("available_tons", flat=True)
    return render(
        request,
        "core/warehouse_portal.html",
        build_context(
            request,
            warehouses_count=warehouses_count,
            bookings_count=bookings_count,
            available_capacity=sum(available_capacity) if available_capacity else 0,
        ),
    )


@login_required
def farmer_market_dashboard(request):
    if request.user.role != "farmer":
        return redirect(get_dashboard_url_for_role(request.user.role))
    return market_data_dashboard(request)


@login_required
def farmer_storage_dashboard(request):
    if request.user.role != "farmer":
        return redirect(get_dashboard_url_for_role(request.user.role))
    return storage(request)


@login_required
def buyer_market_dashboard(request):
    if request.user.role != "buyer":
        return redirect(get_dashboard_url_for_role(request.user.role))
    return marketplace(request)


@login_required
def buyer_storage_dashboard(request):
    if request.user.role != "buyer":
        return redirect(get_dashboard_url_for_role(request.user.role))
    return redirect("buyer-portal")


@login_required
def warehouse_market_dashboard(request):
    if request.user.role != "warehouse_owner":
        return redirect(get_dashboard_url_for_role(request.user.role))
    return redirect("warehouse-portal")


@login_required
def warehouse_bookings_dashboard(request):
    if request.user.role != "warehouse_owner":
        return redirect(get_dashboard_url_for_role(request.user.role))

    seed_warehouses()
    warehouses = Warehouse.objects.filter(owner=request.user)
    bookings = WarehouseBooking.objects.filter(warehouse__owner=request.user).select_related("farmer", "warehouse")[:20]
    return render(
        request,
        "core/warehouse_bookings_dashboard.html",
        build_context(request, warehouses=warehouses, bookings=bookings),
    )


@login_required
def manage_warehouse(request, warehouse_id=None):
    if request.user.role != "warehouse_owner":
        return redirect(get_dashboard_url_for_role(request.user.role))

    warehouse = None
    if warehouse_id is not None:
        warehouse = get_object_or_404(Warehouse, id=warehouse_id, owner=request.user)

    previous_available_tons = warehouse.available_tons if warehouse else None
    previous_capacity_tons = warehouse.capacity_tons if warehouse else None

    form = WarehouseForm(request.POST or None, request.FILES or None, instance=warehouse)
    localize_form(form, get_language(request))
    if request.method == "POST" and form.is_valid():
        warehouse_item = form.save(commit=False)
        warehouse_item.owner = request.user
        warehouse_item.warehouse_source = "owner"
        if not warehouse_item.scheme_name:
            warehouse_item.scheme_name = "Private Warehouse"
        if not warehouse_item.district_ta:
            warehouse_item.district_ta = warehouse_item.district
        warehouse_item.save()

        messages.success(request, "Warehouse data saved successfully.")
        return redirect("warehouse-portal")

    owned_warehouses = Warehouse.objects.filter(owner=request.user).order_by("district", "name_en")
    return render(
        request,
        "core/manage_warehouse.html",
        build_context(request, form=form, warehouse=warehouse, owned_warehouses=owned_warehouses),
    )


@login_required
def add_crop(request, crop_id=None):
    if request.user.role != "farmer":
        messages.error(request, "Only farmers can add crop listings.")
        return redirect(get_dashboard_url_for_role(request.user.role))

    crop = None
    if crop_id is not None:
        crop = get_object_or_404(CropListing, id=crop_id, farmer=request.user)

    form = CropListingForm(request.POST or None, request.FILES or None, instance=crop)
    localize_form(form, get_language(request))
    if request.method == "POST" and form.is_valid():
        crop_item = form.save(commit=False)
        crop_item.farmer = request.user
        crop_item.save()
        messages.success(request, "Crop listing saved successfully.")
        return redirect("farmer-portal")

    return render(request, "core/add_crop.html", build_context(request, form=form, crop=crop))


def marketplace(request):
    if request.user.is_authenticated and request.user.role == "warehouse_owner":
        return redirect("warehouse-portal")
    language = get_language(request)
    if request.user.is_authenticated and request.user.role == "buyer":
        crops = buyer_visible_crop_listings()
    else:
        crops = CropListing.objects.filter(is_available=True).select_related("farmer")
    crop_cards = [
        {
            "id": crop.id,
            "crop_name": crop.crop_name,
            "quantity": crop.quantity,
            "unit": crop.unit,
            "location": crop.location,
            "expected_price": crop.expected_price,
            "contact": crop.farmer.phone or crop.farmer.email,
            "description": crop.description,
            "image_url": crop_image_url(crop),
            "image_hint": crop_hint(crop.crop_name, language),
            "tamil_name": crop_hint(crop.crop_name, "ta"),
            "price_band": price_band(crop.expected_price, language)["label"],
            "price_band_key": price_band(crop.expected_price, language)["key"],
            "is_farmer_listing": True,
        }
        for crop in crops
    ]

    # Buyers should only see farmer-posted crops and not market-rate feeds.
    if not (request.user.is_authenticated and request.user.role in {"buyer", "warehouse_owner"}):
        crop_cards.extend(load_market_rate_rows())

    return render(request, "core/marketplace.html", build_context(request, crops=crop_cards))


def storage(request):
    if request.user.is_authenticated and request.user.role != "farmer":
        return redirect(get_dashboard_url_for_role(request.user.role))
    seed_warehouses()
    query = normalize_search_query(request.GET.get("q", "").strip())
    warehouses = Warehouse.objects.filter(warehouse_source="excel", owner__isnull=True)
    if query:
        warehouses = (
            warehouses.filter(district__icontains=query)
            | warehouses.filter(district_ta__icontains=query)
            | warehouses.filter(name_en__icontains=query)
            | warehouses.filter(name_ta__icontains=query)
            | warehouses.filter(address_text__icontains=query)
            | warehouses.filter(commodity_details__icontains=query)
        )
    warehouses = warehouses.order_by("district", "name_en")
    paginator = Paginator(warehouses, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "core/storage.html",
        build_context(
            request,
            warehouses=page_obj.object_list,
            page_obj=page_obj,
            search_query=query,
            total_warehouses=paginator.count,
        ),
    )


@login_required
def book_warehouse(request, warehouse_id):
    warehouse = get_object_or_404(Warehouse, id=warehouse_id)
    if request.user.role != "farmer":
        messages.error(request, "Only farmers can book warehouse slots.")
        return redirect(get_dashboard_url_for_role(request.user.role))

    form = WarehouseBookingForm(request.POST or None)
    localize_form(form, get_language(request))
    if request.method == "POST" and form.is_valid():
        booking = form.save(commit=False)
        if booking.quantity_tons > warehouse.available_tons:
            messages.error(request, "Requested quantity is greater than available warehouse space.")
            return render(
                request,
                "core/book_warehouse.html",
                build_context(request, form=form, warehouse=warehouse),
            )
        existing_slot = WarehouseBooking.objects.filter(
            farmer=request.user,
            warehouse=warehouse,
            booking_date=booking.booking_date,
            booking_slot=booking.booking_slot,
        ).exclude(status="cancelled")
        if existing_slot.exists():
            messages.error(request, "You already booked this warehouse slot for that date. Please choose a different slot.")
            return render(
                request,
                "core/book_warehouse.html",
                build_context(request, form=form, warehouse=warehouse),
            )
        slot_booked_tons = WarehouseBooking.objects.filter(
            warehouse=warehouse,
            booking_date=booking.booking_date,
            booking_slot=booking.booking_slot,
        ).exclude(status="cancelled").aggregate(total=Sum("quantity_tons"))["total"] or Decimal("0")
        slot_capacity_ratio = Decimal(str(getattr(settings, "WAREHOUSE_SLOT_CAPACITY_RATIO", 0.40)))
        slot_capacity_limit = Decimal(str(warehouse.capacity_tons)) * slot_capacity_ratio
        if slot_booked_tons + booking.quantity_tons > slot_capacity_limit:
            remaining_for_slot = max(Decimal("0"), slot_capacity_limit - slot_booked_tons)
            messages.error(
                request,
                f"This slot is almost full. Remaining slot capacity is {remaining_for_slot:.2f} tons.",
            )
            return render(
                request,
                "core/book_warehouse.html",
                build_context(
                    request,
                    form=form,
                    warehouse=warehouse,
                    slot_capacity_limit=slot_capacity_limit,
                ),
            )
        booking.farmer = request.user
        booking.warehouse = warehouse
        booking.status = "confirmed"
        booking.save()
        warehouse.available_tons -= int(booking.quantity_tons)
        warehouse.save(update_fields=["available_tons"])

        send_notification_with_sms(
            request.user,
            "booking",
            "Warehouse Booking Confirmed",
            (
                f"Your slot for {booking.crop_name} at {warehouse.name_en} on "
                f"{booking.booking_date} ({booking.get_booking_slot_display()}) is confirmed."
            ),
            related_booking=booking,
        )
        if warehouse.owner:
            send_notification_with_sms(
                warehouse.owner,
                "booking",
                "New Warehouse Booking",
                (
                    f"{request.user.get_full_name() or request.user.phone or request.user.username} "
                    f"booked {booking.quantity_tons} tons for {booking.crop_name} on {booking.booking_date}."
                ),
                related_booking=booking,
            )
        messages.success(request, "Warehouse slot booked successfully.")
        
        return redirect("farmer-portal")

    return render(
        request,
        "core/book_warehouse.html",
        build_context(
            request,
            form=form,
            warehouse=warehouse,
            slot_capacity_limit=Decimal(str(warehouse.capacity_tons)) * Decimal(str(getattr(settings, "WAREHOUSE_SLOT_CAPACITY_RATIO", 0.40))),
        ),
    )


@login_required
def buy_crop(request, crop_id):
    if request.user.role != "buyer":
        return redirect(get_dashboard_url_for_role(request.user.role))

    crop = get_object_or_404(CropListing, id=crop_id, is_available=True)
    crop.image_url = crop_image_url(crop)
    form = PurchaseRequestForm(request.POST or None)
    localize_form(form, get_language(request))
    if request.method == "POST" and form.is_valid():
        purchase = form.save(commit=False)
        purchase.buyer = request.user
        purchase.crop = crop
        purchase.save()
        send_notification_with_sms(
            request.user,
            "purchase",
            "Buy Request Sent",
            (
                f"Your request for {purchase.requested_quantity} {crop.unit} of {crop.crop_name} "
                f"from {crop.location} has been sent to the farmer."
            ),
            related_purchase=purchase,
        )
        send_notification_with_sms(
            crop.farmer,
            "purchase",
            "New Buyer Request",
            (
                f"{request.user.get_full_name() or request.user.phone or request.user.username} requested "
                f"{purchase.requested_quantity} {crop.unit} of {crop.crop_name}."
            ),
            related_purchase=purchase,
        )
        messages.success(request, "Buy request sent to the farmer.")
        return redirect("buyer-portal")

    return render(request, "core/buy_crop.html", build_context(request, form=form, crop=crop))


def live_market_data(request):
    query = normalize_search_query(request.GET.get("q", "").strip())
    language = get_language(request)
    role = request.user.role if request.user.is_authenticated else None
    show_only_farmer_listings = role in {"buyer", "warehouse_owner"}

    market_live = {"items": [], "status": "disabled", "fetched_at": None}
    external_items = []
    if not show_only_farmer_listings:
        market_live = get_realtime_market_data(query)
        external_items = market_live.get("items", [])
    excel_items = [] if show_only_farmer_listings else load_market_rate_rows(query=query)
    if not show_only_farmer_listings and external_items:
        combined = external_items + excel_items
        return JsonResponse({
            "items": combined,
            "updated_at": market_live.get("fetched_at") or timezone.now().strftime("%d %b %Y %I:%M %p"),
            "feed_status": market_live.get("status"),
        })

    if role == "buyer":
        crops = buyer_visible_crop_listings()
    else:
        crops = CropListing.objects.filter(is_available=True).select_related("farmer")
    if query:
        crops = crops.filter(Q(crop_name__icontains=query) | Q(location__icontains=query))
    payload = [
        {
            "crop_name": crop.crop_name,
            "quantity": float(crop.quantity),
            "unit": crop.unit,
            "location": crop.location,
            "expected_price": float(crop.expected_price),
            "contact": crop.farmer.phone or crop.farmer.email or crop.farmer.username,
            "description": crop.description,
            "updated": crop.created_at.strftime("%d %b %Y %I:%M %p"),
            "image_url": crop_image_url(crop),
            "image_hint": crop_hint(crop.crop_name, language),
            "tamil_name": crop_hint(crop.crop_name, "ta"),
            "price_band": price_band(crop.expected_price, language)["label"],
            "price_band_key": price_band(crop.expected_price, language)["key"],
            "source": "local",
            "id": crop.id,
            "is_farmer_listing": True,
        }
        for crop in crops
    ]
    if not show_only_farmer_listings:
        payload.extend(excel_items)
    return JsonResponse({
        "items": payload,
        "updated_at": timezone.now().strftime("%d %b %Y %I:%M %p"),
        "feed_status": "local",
    })


def live_storage_data(request):
    seed_warehouses()
    query = normalize_search_query(request.GET.get("q", "").strip())
    lat = request.GET.get("lat")
    lng = request.GET.get("lng")

    try:
        lat_value = float(lat) if lat is not None else None
        lng_value = float(lng) if lng is not None else None
    except ValueError:
        lat_value = None
        lng_value = None

    # Warehouse feed is intentionally Excel-only now.
    warehouses = Warehouse.objects.filter(warehouse_source="excel", owner__isnull=True)
    if query:
        warehouses = (
            warehouses.filter(district__icontains=query)
            | warehouses.filter(district_ta__icontains=query)
            | warehouses.filter(name_en__icontains=query)
            | warehouses.filter(name_ta__icontains=query)
            | warehouses.filter(address_text__icontains=query)
            | warehouses.filter(commodity_details__icontains=query)
        )
    warehouses = warehouses.order_by("district", "name_en")

    items = []
    for warehouse in warehouses:
        distance = None
        if lat and lng:
            try:
                distance = round(haversine_km(float(lat), float(lng), warehouse.latitude, warehouse.longitude), 1)
            except ValueError:
                distance = None
        items.append(
            {
                "id": warehouse.id,
                "name_en": warehouse.name_en,
                "name_ta": warehouse.name_ta,
                "district": warehouse.district,
                "district_ta": warehouse.district_ta,
                "scheme_name": warehouse.scheme_name or ("Private Warehouse" if warehouse.owner_id else "Warehouse"),
                "available_tons": warehouse.available_tons,
                "capacity_tons": warehouse.capacity_tons,
                "contact_number": warehouse.contact_number,
                "address_text": warehouse.address_text,
                "sector_name": warehouse.sector_name,
                "commodity_details": warehouse.commodity_details,
                "distance_km": distance,
                "image_url": warehouse_image_url(warehouse),
                "source": "local",
                "warehouse_source": (
                    "owner"
                    if warehouse.owner_id
                    else (warehouse.warehouse_source or "local")
                ),
            }
        )

    items.sort(key=lambda item: item["distance_km"] if item["distance_km"] is not None else 10**9)
    return JsonResponse({
        "items": items,
        "updated_at": timezone.now().strftime("%d %b %Y %I:%M %p"),
        "feed_status": "excel",
    })

def set_language(request, language):
    if language in {"en", "ta"}:
        request.session["language"] = language
        if request.user.is_authenticated:
            request.user.preferred_language = language
            request.user.save(update_fields=["preferred_language"])
    next_url = request.GET.get("next") or request.META.get("HTTP_REFERER") or reverse("portal-home")
    return HttpResponseRedirect(next_url)


def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect("login")


@login_required
def add_review(request, reviewed_user_id=None, warehouse_id=None):
    """Add a review for a farmer/buyer or warehouse."""
    reviewed_user = None
    warehouse = None
    
    if reviewed_user_id:
        reviewed_user = get_object_or_404(request.user.__class__, id=reviewed_user_id)
    elif warehouse_id:
        warehouse = get_object_or_404(Warehouse, id=warehouse_id)
    else:
        return Http404("Invalid review target")
    
    form = ReviewForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        review = form.save(commit=False)
        review.reviewer = request.user
        review.reviewed_user = reviewed_user
        review.reviewed_warehouse = warehouse
        review.review_type = "farmer" if reviewed_user else "warehouse"
        review.save()
        
        # Send notification
        target = reviewed_user or warehouse
        send_notification_with_sms(
            target if reviewed_user else (warehouse.owner if warehouse.owner else request.user),
            "review",
            f"New {review.rating}★ Review",
            f"{request.user.get_full_name() or request.user.phone} left a review: {review.title}"
        )
        
        messages.success(request, "Review submitted successfully!")
        return redirect(request.META.get('HTTP_REFERER', 'portal-home'))
    
    return render(request, 'core/add_review.html', build_context(
        request,
        form=form,
        reviewed_user=reviewed_user,
        warehouse=warehouse
    ))


@login_required
def view_reviews(request, user_id=None, warehouse_id=None):
    """View reviews for a user or warehouse."""
    reviews = []
    target_name = ""
    average_rating = 0.0
    
    if user_id:
        user = get_object_or_404(request.user.__class__, id=user_id)
        reviews = Review.objects.filter(reviewed_user=user).select_related('reviewer')
        target_name = user.get_full_name() or user.phone
        average_rating = calculate_user_rating(user)
    elif warehouse_id:
        warehouse = get_object_or_404(Warehouse, id=warehouse_id)
        reviews = Review.objects.filter(reviewed_warehouse=warehouse).select_related('reviewer')
        target_name = warehouse.name_en
        average_rating = get_warehouse_rating(warehouse)
    else:
        return Http404("Invalid review target")
    
    return render(request, 'core/view_reviews.html', build_context(
        request,
        reviews=reviews,
        target_name=target_name,
        average_rating=average_rating,
        review_count=len(reviews)
    ))


@login_required
def advanced_marketplace(request):
    """Advanced marketplace search with filtering and sorting."""
    seed_warehouses()
    
    # Get all farmer listings
    crops = CropListing.objects.filter(is_available=True).select_related('farmer').all()
    
    # Parse filter form
    form = MarketplaceFilterForm(request.GET or None)
    
    # Apply filters
    if request.GET:
        search_query = request.GET.get('search_query', '')
        if search_query:
            normalized_query = normalize_search_query(search_query)
            crops = crops.filter(
                Q(crop_name__icontains=search_query) |
                Q(location__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        min_price = request.GET.get('min_price')
        if min_price:
            try:
                crops = crops.filter(expected_price__gte=float(min_price))
            except ValueError:
                pass
        
        max_price = request.GET.get('max_price')
        if max_price:
            try:
                crops = crops.filter(expected_price__lte=float(max_price))
            except ValueError:
                pass
        
        location = request.GET.get('location', '')
        if location:
            crops = crops.filter(location__icontains=location)
        
        unit = request.GET.get('unit', '')
        if unit:
            crops = crops.filter(unit=unit)
        
        date_from = request.GET.get('date_from')
        if date_from:
            crops = crops.filter(created_at__date__gte=date_from)
        
        date_to = request.GET.get('date_to')
        if date_to:
            crops = crops.filter(created_at__date__lte=date_to)
    
    # Apply sorting
    sort_by = request.GET.get('sort_by', 'newest')
    if sort_by == 'price_low':
        crops = crops.order_by('expected_price')
    elif sort_by == 'price_high':
        crops = crops.order_by('-expected_price')
    else:  # Default to newest
        crops = crops.order_by('-created_at')

    crop_items = list(crops)
    for crop in crop_items:
        crop.image_url = crop_image_url(crop)
        crop.image_hint = crop_hint(crop.crop_name, get_language(request))
    
    # Add market preview data
    market_data = load_market_rate_rows(limit=10)
    
    return render(request, 'core/advanced_marketplace.html', build_context(
        request,
        form=form,
        crops=crop_items,
        market_data=market_data,
        results_count=len(crop_items)
    ))


@login_required
def notifications(request):
    """View and manage user notifications."""
    user_notifications = request.user.notifications.all().order_by('-created_at')[:50]
    
    # Mark as read
    read_id = request.GET.get('read')
    if read_id:
        notification = get_object_or_404(Notification, id=read_id, user=request.user)
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
        return redirect('notifications')
    
    unread_count = request.user.notifications.filter(is_read=False).count()
    
    return render(request, 'core/notifications.html', build_context(
        request,
        notifications=user_notifications,
        unread_count=unread_count
    ))


@login_required
def delete_notification(request, notification_id):
    if request.method != "POST":
        return redirect("notifications")

    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.delete()
    messages.success(request, "Notification deleted successfully.")
    return redirect("notifications")


@login_required
def request_ivr_support(request):
    if request.user.role != "farmer":
        return redirect(get_dashboard_url_for_role(request.user.role))

    phone = request.user.phone
    if not phone:
        messages.error(request, "Add a phone number to use IVR support.")
        return redirect("farmer-portal")

    twiml_url_template = request.build_absolute_uri("/api/ivr/twiml/{call_id}/")
    ivr_call = initiate_ivr_call(request.user, phone, twiml_url_template=twiml_url_template)
    if ivr_call:
        send_notification_with_sms(
            request.user,
            "system",
            "IVR Support Requested",
            "Your Agri Genix IVR support request has been created. We will call your phone shortly.",
        )
        messages.success(request, "IVR support request created successfully.")
    else:
        messages.error(request, "IVR support could not be started right now.")
    return redirect("farmer-portal")


def market_data_dashboard(request):
    """Display farmer market prices grouped by commodity."""
    language = get_language(request)
    if request.user.is_authenticated and request.user.role != "farmer":
        return redirect(get_dashboard_url_for_role(request.user.role))
    search_query = request.GET.get('q', '').strip()
    location_filter = request.GET.get('location', '').strip()
    market_items = load_market_rate_rows(query=search_query)
    if location_filter:
        location_normalized = location_filter.lower()
        market_items = [item for item in market_items if location_normalized in str(item.get("location", "")).lower()]

    commodity_groups = {}
    for item in market_items:
        commodity = item.get("crop_name", "Unknown")
        commodity_groups.setdefault(commodity, []).append(item)

    commodity_cards = []
    for commodity, items in commodity_groups.items():
        prices = [float(item.get("expected_price") or 0) for item in items]
        commodity_cards.append(
            {
                "name": commodity,
                "count": len(items),
                "min_price": min(prices) if prices else 0,
                "max_price": max(prices) if prices else 0,
                "avg_price": (sum(prices) / len(prices)) if prices else 0,
                "image_url": crop_image(commodity),
                "tamil_name": crop_hint(commodity, "ta"),
            }
        )
    commodity_cards.sort(key=lambda item: item["name"].lower())
    paginator = Paginator(commodity_cards, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = build_context(
        request,
        search_query=search_query,
        location_filter=location_filter,
        commodity_cards=page_obj.object_list,
        page_obj=page_obj,
        total_commodities=len(commodity_cards),
        total_market_rows=len(market_items),
    )
    return render(request, 'core/market_dashboard.html', context)


@login_required
def market_commodity_detail(request, commodity_name):
    if request.user.role != "farmer":
        return redirect(get_dashboard_url_for_role(request.user.role))

    location_filter = request.GET.get("location", "").strip()
    list_page = request.GET.get("list_page", "").strip()
    commodity_items = [
        item
        for item in load_market_rate_rows()
        if item.get("crop_name", "").lower() == commodity_name.lower()
    ]
    if location_filter:
        location_normalized = location_filter.lower()
        commodity_items = [
            item for item in commodity_items
            if location_normalized in str(item.get("location", "")).lower()
        ]

    commodity_items.sort(key=lambda item: str(item.get("location", "")).lower())
    paginator = Paginator(commodity_items, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "core/market_commodity_detail.html",
        build_context(
            request,
            commodity_name=commodity_name,
            commodity_items=page_obj.object_list,
            page_obj=page_obj,
            location_filter=location_filter,
            list_page=list_page,
            total_rows=len(commodity_items),
            commodity_tamil_name=crop_hint(commodity_name, "ta"),
            commodity_image=crop_image(commodity_name),
        ),
    )


def ivr_twiml_handler(request, call_id):
    """Handle Twilio IVR TwiML responses."""
    try:
        from twilio.twiml.voice_response import VoiceResponse
    except ImportError:
        return JsonResponse({"error": "IVR service unavailable. Install twilio to enable IVR."}, status=503)
    from .models import IVRCall
    
    # Get or create IVR call record
    ivr_call = get_object_or_404(IVRCall, call_id=call_id)
    ivr_call.status = "in_progress"
    ivr_call.save()
    
    response = VoiceResponse()
    
    # Greeting
    response.say("Welcome to Agri Genix.")
    response.say("Press 1 to hear market rates, 2 for storage availability, or 3 for your bookings.")
    
    # Capture user input
    gather = response.gather(num_digits=1, action=f'/api/ivr/handle/{call_id}/', method='POST')
    gather.say("Press 1, 2, or 3.")
    
    # If no input, loop back
    response.redirect(f'/api/ivr/twiml/{call_id}/')
    
    return HttpResponse(str(response), content_type="application/xml")


def ivr_handle_input(request, call_id):
    """Handle IVR user input."""
    from .models import IVRCall
    try:
        from twilio.twiml.voice_response import VoiceResponse
    except ImportError:
        return JsonResponse({"error": "IVR service unavailable. Install twilio to enable IVR."}, status=503)
    
    ivr_call = get_object_or_404(IVRCall, call_id=call_id)
    response = VoiceResponse()
    
    digits = request.POST.get('Digits', '')
    
    if digits == '1':
        market_items = get_realtime_market_data("").get("items", []) or load_market_rate_rows(limit=2)
        if market_items:
            first = market_items[0]
            second = market_items[1] if len(market_items) > 1 else None
            response.say(
                f"Latest market update. {first.get('crop_name', 'Crop')} is around {first.get('expected_price', 0)} rupees per kilogram in {first.get('location', 'your market')}."
            )
            if second:
                response.say(
                    f"{second.get('crop_name', 'Another crop')} is around {second.get('expected_price', 0)} rupees per kilogram in {second.get('location', 'your market')}."
                )
        else:
            response.say("Market data is not available right now.")
        ivr_call.action_taken = "Checked market rates"
    elif digits == '2':
        warehouse = Warehouse.objects.filter(available_tons__gt=0).order_by("-available_tons").first()
        if warehouse:
            response.say(
                f"Storage update. {warehouse.name_en} in {warehouse.district} has {warehouse.available_tons} tons available."
            )
        else:
            response.say("No warehouse storage data is available right now.")
        ivr_call.action_taken = "Checked storage"
    elif digits == '3':
        booking = WarehouseBooking.objects.filter(farmer=ivr_call.user).select_related("warehouse").first()
        if booking:
            response.say(
                f"Your latest booking is for {booking.crop_name} at {booking.warehouse.name_en} on {booking.booking_date} during {booking.get_booking_slot_display()}."
            )
        else:
            response.say("You do not have any active warehouse bookings right now.")
        ivr_call.action_taken = "Checked bookings"
    else:
        response.say("Invalid input. Goodbye.")
        ivr_call.action_taken = "Invalid input"
    
    ivr_call.status = "completed"
    ivr_call.ended_at = timezone.now()
    ivr_call.save()
    
    return HttpResponse(str(response), content_type="application/xml")


@login_required
def farmer_bookings_dashboard(request):
    if request.user.role != "farmer":
        return redirect(get_dashboard_url_for_role(request.user.role))
    
    bookings = WarehouseBooking.objects.filter(farmer=request.user).select_related("warehouse").order_by("-created_at")
    return render(
        request,
        "core/farmer_bookings.html",
        build_context(request, bookings=bookings),
    )


@login_required
def cancel_warehouse_booking(request, booking_id):
    if request.user.role != "farmer":
        return redirect(get_dashboard_url_for_role(request.user.role))
        
    booking = get_object_or_404(WarehouseBooking, id=booking_id, farmer=request.user)
    
    if request.method == "POST":
        if booking.status in ["confirmed", "pending"]:
            booking.status = "cancelled"
            booking.save(update_fields=["status"])
            
            # Restore capacity
            warehouse = booking.warehouse
            warehouse.available_tons += int(booking.quantity_tons)
            # Ensure we don't exceed max capacity
            warehouse.available_tons = min(warehouse.available_tons, warehouse.capacity_tons)
            warehouse.save(update_fields=["available_tons"])

            send_notification_with_sms(
                request.user,
                "system",
                "Booking Cancelled",
                (
                    f"Your booking for {booking.crop_name} at {warehouse.name_en} on "
                    f"{booking.booking_date} has been cancelled."
                ),
            )
            
            messages.success(request, f"Booking for {booking.crop_name} at {warehouse.name_en} successfully cancelled.")
        else:
            messages.error(request, "This booking cannot be cancelled.")
            
    return redirect("farmer-bookings-dashboard")


@login_required
def delete_warehouse_booking(request, booking_id):
    if request.user.role != "farmer":
        return redirect(get_dashboard_url_for_role(request.user.role))

    if request.method != "POST":
        return redirect("farmer-bookings-dashboard")

    booking = get_object_or_404(WarehouseBooking, id=booking_id, farmer=request.user)
    warehouse = booking.warehouse

    if booking.status in ["confirmed", "pending"]:
        warehouse.available_tons += int(booking.quantity_tons)
        warehouse.available_tons = min(warehouse.available_tons, warehouse.capacity_tons)
        warehouse.save(update_fields=["available_tons"])

    crop_name = booking.crop_name
    booking_date = booking.booking_date
    slot_name = booking.get_booking_slot_display()
    booking.delete()

    send_notification_with_sms(
        request.user,
        "system",
        "Booking Slot Deleted",
        f"Your booking slot for {crop_name} on {booking_date} ({slot_name}) has been deleted.",
    )

    messages.success(request, "Booking slot deleted successfully.")
    return redirect("farmer-bookings-dashboard")
