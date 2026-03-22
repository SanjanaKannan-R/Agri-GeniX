import random
import json
import re
import zipfile
import zlib
import csv
import xml.etree.ElementTree as ET
from datetime import timedelta
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
from urllib.parse import urlencode, urlparse, parse_qsl, urljoin
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.utils import timezone

from .mongo import write_mongo_event
from .models import FarmerUser, OTPRequest, Warehouse

XLSX_NS = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def normalize_identifier(identifier):
    return identifier.strip().lower()


TAMIL_ALIASES = {
    "nel": "rice",
    "nellu": "rice",
    "arisi": "rice",
    "thakkali": "tomato",
    "thakali": "tomato",
    "vengayam": "onion",
    "verkadalai": "groundnut",
    "kadala": "groundnut",
    "urulaikilangu": "potato",
    "urulai": "potato",
    "vazhakkai": "banana",
    "vaazhai": "banana",
    "milagai": "chilli",
    "kathirikka": "brinjal",
    "vendakkai": "okra",
    "thengai": "coconut",
    "cholam": "maize",
    "karumbu": "sugarcane",
    "kothamalli": "coriander",
    "murungakkai": "drumstick",
    "kidangu": "warehouse",
    "godown": "warehouse",
    "kudon": "warehouse",
}

WAREHOUSE_DEFAULT_IMAGE = "https://commons.wikimedia.org/wiki/Special:Redirect/file/Warehouse%20Building.jpg"


CROP_VISUALS = [
    {
        "keywords": (
            "paddy", "rice", "nel", "nellu", "arisi", "bajra", "jowar", "ragi",
            "wheat", "small millets", "millets", "korra", "samai", "varagu",
            "other cereals", "foodgrain", "sannhamp", "mesta",
        ),
        "image": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Rice%20Plants%20%28IRRI%29.jpg",
        "hint_en": "Green paddy grain bundle picture",
        "label_ta": "நெல் / அரிசி",
    },
    {
        "keywords": ("tomato", "thakkali", "thakali"),
        "image": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Tomato%20%281%29.jpg",
        "hint_en": "Fresh red tomato picture",
        "label_ta": "தக்காளி",
    },
    {
        "keywords": (
            "groundnut", "peanut", "verkadalai", "kadalai", "arhar", "tur",
            "gram", "moong", "urad", "horse-gram", "pulses", "soyabean",
            "sunflower", "sesamum", "guar seed", "rapeseed", "mustard",
            "castor seed", "cashewnut", "arecanut",
        ),
        "image": "https://commons.wikimedia.org/wiki/Special:Redirect/file/An_Harvest_of_Joy.jpg",
        "hint_en": "Brown groundnut pods picture",
        "label_ta": "நிலக்கடலை",
    },
    {
        "keywords": ("onion", "vengayam"),
        "image": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Onion%20%28Allium%20cepa%29.jpg",
        "hint_en": "Purple onion bulb picture",
        "label_ta": "வெங்காயம்",
    },
    {
        "keywords": ("apple",),
        "image": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Red-Apple-Bio-Natural_61389-480x360_%284899674471%29.jpg",
        "hint_en": "Red apple picture",
        "label_ta": "Apple",
    },
    {
        "keywords": ("grapes", "grape"),
        "image": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Ars_grape_bunch.jpg",
        "hint_en": "Grape bunch picture",
        "label_ta": "Grapes",
    },
    {
        "keywords": (
            "banana", "vaazhai", "vazhakkai", "mango", "orange", "citrus",
            "papaya", "pineapple", "peach", "jack fruit",
            "water melon", "other fresh fruits", "pome fruit", "pome granet",
        ),
        "image": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Banana%20%281%29.jpg",
        "hint_en": "Yellow banana bunch picture",
        "label_ta": "வாழை / வாழைக்காய்",
    },
    {
        "keywords": ("brinjal", "eggplant", "aubergine", "kathirikka"),
        "image": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Brinjal.jpg",
        "hint_en": "Purple brinjal picture",
        "label_ta": "கத்திரிக்காய்",
    },
    {
        "keywords": ("chilli", "chili", "milagai"),
        "image": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Chilli%20%28247798751%29.jpeg",
        "hint_en": "Green and red chilli picture",
        "label_ta": "மிளகாய்",
    },
    {
        "keywords": ("peas", "pea", "avare", "mattar", "green peas"),
        "image": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Peas_in_pods_-_Studio.jpg",
        "hint_en": "Green peas in pods picture",
        "label_ta": "Peas / Avare",
    },
    {
        "keywords": (
            "okra", "ladyfinger", "vendakkai", "bhindi", "beans", "mutter",
            "bitter gourd", "bottle gourd", "ash gourd", "cucumber",
            "lab-lab", "ribed guard", "snak guard", "other vegetables",
            "cauliflower", "cabbage", "pump kin",
        ),
        "image": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Okra%20%28also%20called%20lady%E2%80%99s%20finger%29.jpg",
        "hint_en": "Fresh okra pods picture",
        "label_ta": "வெண்டைக்காய்",
    },
    {
        "keywords": (
            "potato", "urulai", "urulaikilangu", "sweet potato", "tapioca",
            "yam", "beet root", "redish", "turmeric",
            "black pepper", "cardamom", "tobacco",
        ),
        "image": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Potatos.jpg",
        "hint_en": "Brown potato basket picture",
        "label_ta": "உருளைக்கிழங்கு",
    },
    {
        "keywords": ("carrot",),
        "image": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Foot_carrot_%28cropped%29.jpg",
        "hint_en": "Carrot picture",
        "label_ta": "Carrot",
    },
    {
        "keywords": ("ginger", "dry ginger"),
        "image": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Ginger2.jpg",
        "hint_en": "Ginger root picture",
        "label_ta": "Ginger",
    },
    {
        "keywords": ("garlic",),
        "image": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Garlic_%28199386734%29.jpg",
        "hint_en": "Garlic bulb picture",
        "label_ta": "Garlic",
    },
    {
        "keywords": ("coconut", "thengai"),
        "image": "https://commons.wikimedia.org/wiki/Special:Redirect/file/%22Coconut%22.jpg",
        "hint_en": "Split coconut picture",
        "label_ta": "தேங்காய்",
    },
    {
        "keywords": ("maize", "corn", "cholam", "total foodgrain"),
        "image": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Maize%20%28corn%29.jpg",
        "hint_en": "Golden maize cob picture",
        "label_ta": "மக்காச்சோளம்",
    },
    {
        "keywords": ("sugarcane", "karumbu"),
        "image": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Sugarcane%2001.jpg",
        "hint_en": "Sugarcane stalk picture",
        "label_ta": "கரும்பு",
    },
    {
        "keywords": ("coriander", "cilantro", "kothamalli"),
        "image": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Coriander%2003.jpg",
        "hint_en": "Fresh coriander leaves picture",
        "label_ta": "கொத்தமல்லி",
    },
    {
        "keywords": ("drumstick", "murungakkai"),
        "image": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Moringa%20oleifera%20drumstick%20pods.JPG",
        "hint_en": "Long drumstick vegetable picture",
        "label_ta": "முருங்கைக்காய்",
    },
]


def crop_visual(crop_name):
    crop = (crop_name or "").lower()
    for item in CROP_VISUALS:
        if any(keyword in crop for keyword in item["keywords"]):
            return item
    return {
        "image": "https://commons.wikimedia.org/wiki/Special:Redirect/file/Rice%20Plants%20%28IRRI%29.jpg",
        "hint_en": "Crop image",
        "label_ta": "",
    }


def normalize_search_query(query):
    cleaned = normalize_identifier(query)
    tokens = cleaned.split()
    expanded = []
    for token in tokens:
        expanded.append(token)
        alias = TAMIL_ALIASES.get(token)
        if alias and alias not in expanded:
            expanded.append(alias)
    return " ".join(expanded).strip()


def resolve_user(identifier, role):
    identifier = normalize_identifier(identifier)
    if "@" in identifier:
        user = FarmerUser.objects.filter(email__iexact=identifier).first()
        if not user:
            user = FarmerUser.objects.create_user(
                username=identifier.replace("@", "_"),
                email=identifier,
                role=role,
                preferred_language="en",
            )
        elif user.role != role:
            user.role = role
            user.save(update_fields=["role"])
    else:
        digits = "".join(ch for ch in identifier if ch.isdigit())
        user = FarmerUser.objects.filter(phone=digits).first()
        if not user:
            user = FarmerUser.objects.create_user(
                username=f"user_{digits}",
                phone=digits,
                role=role,
                preferred_language="en",
            )
        elif user.role != role:
            user.role = role
            user.save(update_fields=["role"])
        identifier = digits
    return user, identifier


def create_otp(user, identifier):
    code = f"{random.randint(100000, 999999)}"
    return OTPRequest.objects.create(
        user=user,
        identifier=identifier,
        code=code,
        expires_at=timezone.now() + timedelta(minutes=settings.OTP_EXPIRY_MINUTES),
    )


def dispatch_otp(request, identifier, code):
    provider = settings.SMS_PROVIDER
    message = f"Your Agri Genix OTP is {code}. It will expire in {settings.OTP_EXPIRY_MINUTES} minutes."

    if provider == "twilio":
        try:
            from twilio.rest import Client

            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            if "@" in identifier:
                messages.info(request, "Twilio email is not configured. Demo OTP is shown below.")
                messages.success(request, f"Demo OTP: {code}")
                return
            client.messages.create(
                body=message,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=identifier,
            )
            messages.success(request, "OTP sent successfully.")
            return
        except Exception:
            messages.warning(request, "Live SMS could not be sent. Falling back to demo OTP.")

    print(message)
    messages.success(request, f"Demo OTP: {code}")


def seed_warehouses():
    imported = sync_warehouse_data_from_excel()
    if imported:
        return

    Warehouse.objects.bulk_create(
        [
            Warehouse(
                name_en="Thanjavur Central Warehouse",
                name_ta="தஞ்சாவூர் மத்திய கிடங்கு",
                district="Thanjavur",
                district_ta="தஞ்சாவூர்",
                scheme_name="Govt Storage",
                warehouse_source="demo",
                latitude=10.7867,
                longitude=79.1378,
                capacity_tons=500,
                available_tons=180,
                contact_number="Contact in app",
            ),
            Warehouse(
                name_en="Trichy Farmers Storage",
                name_ta="திருச்சி விவசாயிகள் கிடங்கு",
                district="Tiruchirappalli",
                district_ta="திருச்சிராப்பள்ளி",
                scheme_name="Farmer Storage",
                warehouse_source="demo",
                latitude=10.7905,
                longitude=78.7047,
                capacity_tons=320,
                available_tons=95,
                contact_number="Contact in app",
            ),
            Warehouse(
                name_en="Madurai Agro Godown",
                name_ta="மதுரை அக்ரோ கிடங்கு",
                district="Madurai",
                district_ta="மதுரை",
                scheme_name="Agro Godown",
                warehouse_source="demo",
                latitude=9.9252,
                longitude=78.1198,
                capacity_tons=410,
                available_tons=140,
                contact_number="Contact in app",
            ),
        ]
    )


def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return 6371 * c


def crop_image(crop_name):
    return crop_visual(crop_name)["image"]


def crop_hint(crop_name, language="en"):
    visual = crop_visual(crop_name)
    if language == "ta":
        return visual["label_ta"] or crop_name
    return visual["hint_en"]


def normalize_market_price(crop_name, raw_price):
    try:
        raw = float(raw_price)
    except (TypeError, ValueError):
        return 0.0

    if raw <= 0:
        return 0.0

    crop = (crop_name or "").lower()
    ranges = [
        (("rice", "paddy"), (20, 100)),
        (("tur", "arhar", "dal", "gram"), (60, 250)),
        (("bajra", "jowar", "ragi", "maize"), (15, 80)),
        (("banana", "tapioca", "sweet potato", "sugarcane"), (5, 60)),
        (("groundnut", "peanut", "sunflower", "castor"), (30, 150)),
        (("coconut",), (15, 80)),
        (("coriander", "dry chillies", "chillies"), (20, 500)),
        (("cotton",), (40, 120)),
        (("cashewnut",), (80, 1200)),
        (("onion",), (8, 60)),
    ]

    lower_bound, upper_bound = 10, 300
    for keys, bounds in ranges:
        if any(key in crop for key in keys):
            lower_bound, upper_bound = bounds
            break

    candidates = []
    for power in range(-6, 3):
        candidate = raw * (10 ** power)
        if candidate > 0:
            candidates.append(candidate)

    def score(value):
        if lower_bound <= value <= upper_bound:
            return 0, abs(value - ((lower_bound + upper_bound) / 2))
        if value < lower_bound:
            return 1, lower_bound - value
        return 1, value - upper_bound

    best = min(candidates, key=score)
    if best < lower_bound:
        best = float(lower_bound)
    elif best > upper_bound:
        best = float(upper_bound)

    return round(best, 2)


def price_band(price, language="en"):
    try:
        value = float(price)
    except (TypeError, ValueError):
        value = 0

    if value < 25:
        return {"key": "low", "label": "குறைவு" if language == "ta" else "Low"}
    if value < 80:
        return {"key": "medium", "label": "நடுத்தரம்" if language == "ta" else "Medium"}
    return {"key": "high", "label": "உயர்" if language == "ta" else "High"}


def _fetch_json(url, params=None, headers=None):
    if not url:
        return None
    params = params or {}
    headers = headers or {}
    parsed = urlparse(url)
    existing = dict(parse_qsl(parsed.query))
    merged = {**existing, **{k: v for k, v in params.items() if v not in (None, "")}}
    final_url = parsed._replace(query=urlencode(merged)).geturl()
    request = Request(final_url, headers=headers)
    with urlopen(request, timeout=12) as response:
        return json.loads(response.read().decode("utf-8"))


def _resolve_api_url(path_or_url, base_url=""):
    if not path_or_url:
        return ""
    if path_or_url.startswith(("http://", "https://")):
        return path_or_url
    base = (base_url or "").rstrip("/") + "/"
    return urljoin(base, path_or_url.lstrip("/"))


def _fetch_json_variants(url, param_sets=None, header_sets=None):
    param_sets = param_sets or [{}]
    header_sets = header_sets or [{}]
    last_error = None

    for params in param_sets:
        for headers in header_sets:
            try:
                return _fetch_json(url, params=params, headers=headers)
            except Exception as exc:
                last_error = exc

    if last_error:
        raise last_error
    return None


def _cache_key(prefix, query="", lat=None, lng=None):
    safe_query = (query or "").strip().lower()
    return f"agrigenix:{prefix}:{safe_query}:{lat}:{lng}"


def _cache_payload(prefix, items, query="", lat=None, lng=None):
    payload = {
        "items": items,
        "fetched_at": timezone.now().strftime("%d %b %Y %I:%M %p"),
        "status": "live",
    }
    cache.set(
        _cache_key(prefix, query=query, lat=lat, lng=lng),
        payload,
        timeout=getattr(settings, "LIVE_DATA_CACHE_TIMEOUT", 300),
    )
    write_mongo_event(
        "live_feed_snapshots",
        {
            "feed": prefix,
            "query": query,
            "lat": lat,
            "lng": lng,
            "items_count": len(items),
            "status": "live",
            "created_at": timezone.now(),
        },
    )
    return payload


def _cached_payload(prefix, query="", lat=None, lng=None):
    return cache.get(_cache_key(prefix, query=query, lat=lat, lng=lng))


def _extract_records(payload):
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    direct_keys = {"crop_name", "commodity", "Commodity", "warehouse_name", "godown_name", "name"}
    if direct_keys.intersection(payload.keys()):
        return [payload]
    for key in ("records", "items", "results", "data"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            for nested_key in ("records", "items", "results", "data"):
                nested_value = value.get(nested_key)
                if isinstance(nested_value, list):
                    return nested_value
    for key in ("response", "result", "respObj", "responseData", "payload"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            nested_records = _extract_records(value)
            if nested_records:
                return nested_records
    return []


def _read_xlsx_rows(path):
    xlsx_path = Path(path)
    if not xlsx_path.exists():
        return []

    with zipfile.ZipFile(xlsx_path) as zf:
        shared_strings = []
        if "xl/sharedStrings.xml" in zf.namelist():
            root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in root.findall("a:si", XLSX_NS):
                shared_strings.append("".join(node.text or "" for node in si.iterfind(".//a:t", XLSX_NS)))

        workbook = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        rel_map = {rel.attrib.get("Id"): rel.attrib.get("Target") for rel in rels}

        first_sheet = workbook.find("a:sheets/a:sheet", XLSX_NS)
        if first_sheet is None:
            return []
        target = rel_map[first_sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")]
        sheet_path = f"xl/{target}"
        sheet = ET.fromstring(zf.read(sheet_path))

        rows = []
        for row in sheet.findall(".//a:sheetData/a:row", XLSX_NS):
            row_values = {}
            for cell in row.findall("a:c", XLSX_NS):
                ref = cell.attrib.get("r", "")
                match = re.match(r"([A-Z]+)", ref)
                column = match.group(1) if match else ref
                cell_type = cell.attrib.get("t")
                value_node = cell.find("a:v", XLSX_NS)
                value = ""
                if cell_type == "inlineStr":
                    text_node = cell.find("a:is/a:t", XLSX_NS)
                    value = text_node.text if text_node is not None else ""
                elif value_node is not None:
                    value = value_node.text or ""
                    if cell_type == "s":
                        try:
                            value = shared_strings[int(value)]
                        except Exception:
                            pass
                row_values[column] = value
            rows.append(row_values)
        return rows


def _decode_pdf_text(value):
    output = []
    index = 0
    while index < len(value):
        char = value[index]
        if char == "\\" and index + 1 < len(value):
            next_char = value[index + 1]
            mapping = {
                "n": "\n",
                "r": "\r",
                "t": "\t",
                "b": "\b",
                "f": "\f",
                "(": "(",
                ")": ")",
                "\\": "\\",
            }
            if next_char in mapping:
                output.append(mapping[next_char])
                index += 2
                continue
        output.append(char)
        index += 1
    return "".join(output)


def _clean_pdf_text(value):
    value = (value or "").replace("\\", " ")
    value = re.sub(r"\s+", " ", value)
    value = value.replace(" ,", ",").replace(" .", ".")
    value = value.replace(" - ", "-")
    return value.strip(" ,")


def _extract_pdf_entries(path):
    pdf_path = Path(path)
    if not pdf_path.exists():
        return []

    entries_by_chunk = []
    data = pdf_path.read_bytes()
    for match in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.S):
        try:
            chunk = zlib.decompress(match.group(1)).decode("latin1", errors="ignore")
        except Exception:
            continue

        entries = []
        for block in re.finditer(r"BT(.*?)ET", chunk, re.S):
            segment = block.group(1)
            position = re.search(r"1 0 0 1 ([0-9.]+) ([0-9.]+) Tm", segment)
            if not position:
                continue

            x = float(position.group(1))
            y = float(position.group(2))
            parts = []
            for array in re.findall(r"\[(.*?)\]\s*TJ", segment, re.S):
                for item in re.findall(r"\((.*?)\)", array, re.S):
                    parts.append(_decode_pdf_text(item))
            for item in re.findall(r"\((.*?)\)\s*Tj", segment, re.S):
                parts.append(_decode_pdf_text(item))

            text = _clean_pdf_text("".join(parts))
            if text:
                entries.append((y, x, text))

        capacity_entries = [
            (y, x, text)
            for y, x, text in entries
            if 470 <= x < 540 and re.fullmatch(r"[0-9.]+", text)
        ]
        if len(capacity_entries) >= 2:
            entries_by_chunk.append(entries)
    return entries_by_chunk


def _extract_district_from_address(address):
    address = _clean_pdf_text(address)
    if not address:
        return ""

    for pattern in (
        r"([A-Za-z&.' -]+?)\s+District",
        r"([A-Za-z&.' -]+?)\s+Taluk\s*&\s*District",
    ):
        matches = re.findall(pattern, address, flags=re.I)
        if matches:
            candidate = re.sub(r".*,", "", matches[-1]).strip()
            candidate = re.sub(r"\bTaluk\b.*", "", candidate, flags=re.I).strip(" ,-")
            if candidate:
                return candidate
    return ""


def load_godown_pdf_rows():
    chunk_entries = _extract_pdf_entries(settings.GODOWN_ADDRESSES_PDF)
    rows = []
    seen_keys = set()
    skip_names = {
        "Name & Address",
        "Nam e & Address",
        "Addresses of Rural Godowns",
    }
    skip_text = {
        "Addresses of Rural Godowns",
        "Tamil",
        "Nadu",
        "&",
        "Puducherry",
        "Name & Address",
        "Nam e & Address",
        "showing Survey/Plot/Gut No.",
        "Village,Taluka, District and State.",
        "Capacity",
        "(MT)",
        "Sector",
        "Commodity",
        "stored",
    }

    for entries in chunk_entries:
        capacities = sorted(
            [
                (y, x, text)
                for y, x, text in entries
                if 470 <= x < 540 and re.fullmatch(r"[0-9.]+", text)
            ],
            reverse=True,
        )
        for index, (y, _, capacity_text) in enumerate(capacities):
            upper = 10**9 if index == 0 else (capacities[index - 1][0] + y) / 2
            lower = -10**9 if index == len(capacities) - 1 else (y + capacities[index + 1][0]) / 2

            left_entries = [
                (yy, xx, text)
                for yy, xx, text in entries
                if xx < 470 and lower < yy <= upper and text not in skip_text
            ]
            if not left_entries:
                continue

            grouped_rows = {}
            for yy, xx, text in left_entries:
                grouped_rows.setdefault(round(yy, 2), []).append((xx, text))

            left_lines = [
                _clean_pdf_text(" ".join(text for _, text in sorted(values)))
                for _, values in sorted(grouped_rows.items(), reverse=True)
            ]
            left_lines = [line for line in left_lines if line]
            if not left_lines:
                continue

            name = left_lines[0]
            if name in skip_names:
                continue

            address = _clean_pdf_text(" ".join(left_lines[1:]))
            sector = _clean_pdf_text(
                " ".join(
                    text
                    for yy, xx, text in entries
                    if 540 <= xx < 595 and lower < yy <= upper and text not in skip_text
                )
            )
            commodity = _clean_pdf_text(
                " ".join(
                    text
                    for yy, xx, text in entries
                    if xx >= 595 and lower < yy <= upper and text not in skip_text
                )
            )
            try:
                capacity_tons = int(round(float(capacity_text)))
            except (TypeError, ValueError):
                continue

            district = _extract_district_from_address(address) or "Tamil Nadu"
            key = (name.lower(), district.lower(), capacity_tons)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            rows.append(
                {
                    "district": district,
                    "district_ta": district,
                    "name_en": name,
                    "name_ta": name,
                    "scheme_name": sector or "Rural Godown",
                    "capacity_tons": capacity_tons,
                    "address_text": address,
                    "sector_name": sector,
                    "commodity_details": commodity,
                    "contact_number": "Address available",
                }
            )
    return rows


def load_warehouse_rows():
    master_rows = _read_xlsx_rows(settings.GODOWN_MASTER_XLSX)
    merged = []
    for row in master_rows:
        if not row.get("B") or not row.get("C"):
            continue
        district = row.get("B", "").strip()
        name = row.get("C", "").strip()
        scheme_name = row.get("D", "").strip()
        try:
            capacity_tons = int(float(row.get("E", 0) or 0))
        except (TypeError, ValueError):
            capacity_tons = 0
        if not district or not name or capacity_tons <= 0:
            continue
        merged.append(
            {
                "district": district,
                "district_ta": district,
                "name_en": name,
                "name_ta": name,
                "scheme_name": scheme_name or "Rural Godown",
                "capacity_tons": capacity_tons,
                "address_text": "",
                "sector_name": "",
                "commodity_details": "",
                "contact_number": "Address available",
            }
        )

    existing_keys = {(item["name_en"].lower(), item["district"].lower()) for item in merged}
    for row in load_godown_pdf_rows():
        key = (row["name_en"].lower(), row["district"].lower())
        if key in existing_keys:
            continue
        merged.append(row)
        existing_keys.add(key)
    return merged


def sync_warehouse_data_from_excel():
    rows = load_warehouse_rows()
    if not rows:
        return False

    dedupe_seen = set()
    for warehouse in Warehouse.objects.filter(warehouse_source="excel", owner__isnull=True).order_by("id"):
        dedupe_key = (warehouse.name_en.lower(), warehouse.district.lower())
        if dedupe_key in dedupe_seen:
            warehouse.warehouse_source = "legacy"
            warehouse.save(update_fields=["warehouse_source"])
            continue
        dedupe_seen.add(dedupe_key)

    active_keys = {(row["name_en"].lower(), row["district"].lower()) for row in rows}
    for stale in Warehouse.objects.filter(warehouse_source="excel", owner__isnull=True):
        stale_key = (stale.name_en.lower(), stale.district.lower())
        if stale_key not in active_keys:
            stale.warehouse_source = "legacy"
            stale.save(update_fields=["warehouse_source"])

    existing = {
        (w.name_en.lower(), w.district.lower()): w
        for w in Warehouse.objects.exclude(warehouse_source="legacy").order_by("id")
    }
    created = False
    for index, row in enumerate(rows):
        key = (row["name_en"].lower(), row["district"].lower())
        if key in existing:
            warehouse = existing[key]
            updated = False
            if warehouse.name_ta != row["name_ta"]:
                warehouse.name_ta = row["name_ta"]
                updated = True
            if warehouse.district_ta != row["district_ta"]:
                warehouse.district_ta = row["district_ta"]
                updated = True
            if warehouse.scheme_name != row["scheme_name"]:
                warehouse.scheme_name = row["scheme_name"]
                updated = True
            if warehouse.address_text != row.get("address_text", ""):
                warehouse.address_text = row.get("address_text", "")
                updated = True
            if warehouse.sector_name != row.get("sector_name", ""):
                warehouse.sector_name = row.get("sector_name", "")
                updated = True
            if warehouse.commodity_details != row.get("commodity_details", ""):
                warehouse.commodity_details = row.get("commodity_details", "")
                updated = True
            if warehouse.contact_number != row.get("contact_number", warehouse.contact_number):
                warehouse.contact_number = row.get("contact_number", warehouse.contact_number)
                updated = True
            if not warehouse.owner_id and warehouse.warehouse_source != "excel":
                warehouse.warehouse_source = "excel"
                updated = True
            if warehouse.capacity_tons != row["capacity_tons"]:
                warehouse.capacity_tons = row["capacity_tons"]
                warehouse.available_tons = min(max(warehouse.available_tons, 0), row["capacity_tons"])
                updated = True
            if updated:
                warehouse.save()
            continue
        latitude = 10.6 + (index % 10) * 0.18
        longitude = 77.8 + (index % 7) * 0.22
        created_warehouse = Warehouse.objects.create(
            name_en=row["name_en"],
            name_ta=row["name_ta"],
            district=row["district"],
            district_ta=row["district_ta"],
            scheme_name=row["scheme_name"],
            warehouse_source="excel",
            latitude=latitude,
            longitude=longitude,
            capacity_tons=row["capacity_tons"],
            available_tons=row["capacity_tons"],
            contact_number=row.get("contact_number", "Address available"),
            address_text=row.get("address_text", ""),
            sector_name=row.get("sector_name", ""),
            commodity_details=row.get("commodity_details", ""),
        )
        existing[key] = created_warehouse
        created = True
    return created or Warehouse.objects.exists()


def load_market_rate_rows(limit=None, query=""):
    csv_path = Path(settings.MARKET_PRICES_CSV)
    if csv_path.exists():
        items = []
        query_lower = query.lower().strip()
        with csv_path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                crop_name = (row.get("Commodity") or "").strip()
                district = (row.get("District") or "").strip()
                market = (row.get("Market") or "").strip()
                variety = (row.get("Variety") or "").strip()
                arrival_date = (row.get("Arrival_Date") or "").strip()
                if not crop_name or not district:
                    continue
                haystack = " ".join([crop_name, district, market, variety]).lower()
                if query_lower and query_lower not in haystack:
                    continue

                modal_price = row.get("Modal_x0020_Price") or row.get("Max_x0020_Price") or row.get("Min_x0020_Price") or 0
                rate = normalize_market_price(crop_name, modal_price)
                band = price_band(rate)
                location = f"{district} - {market}" if market else district
                description_parts = [part for part in [variety, arrival_date] if part]
                items.append(
                    {
                        "crop_name": crop_name,
                        "quantity": 1,
                        "unit": "kg",
                        "location": location,
                        "expected_price": round(rate, 2),
                        "contact": "Tamil Nadu market prices",
                        "description": " | ".join(description_parts) if description_parts else "CSV market price",
                        "updated": arrival_date or "CSV data",
                        "image_url": crop_image(crop_name),
                        "image_hint": crop_hint(crop_name),
                        "tamil_name": crop_hint(crop_name, "ta"),
                        "price_band": band["label"],
                        "price_band_key": band["key"],
                        "source": "csv",
                        "is_farmer_listing": False,
                    }
                )
                if limit is not None and len(items) >= limit:
                    break
        return items

    rows = _read_xlsx_rows(settings.CROP_RATES_XLSX)
    if len(rows) < 3:
        return []

    data_rows = rows[2:] if rows[0].get("A") == "Tamil Nadu Crop Rates" else rows[1:]
    items = []
    query_lower = query.lower().strip()
    for row in data_rows:
        crop_name = (row.get("C") or "").strip()
        district = (row.get("A") or "").strip()
        season = (row.get("B") or "").strip()
        if not crop_name or not district:
            continue
        if query_lower and query_lower not in crop_name.lower() and query_lower not in district.lower():
            continue
        rate = normalize_market_price(crop_name, row.get("F") or 0)
        band = price_band(rate)
        items.append(
            {
                "crop_name": crop_name,
                "quantity": float(row.get("E") or 0),
                "unit": "kg",
                "location": district,
                "expected_price": round(rate, 2),
                "contact": "Tamil Nadu market data",
                "description": season or "Excel market rate",
                "updated": "Excel data",
                "image_url": crop_image(crop_name),
                "image_hint": crop_hint(crop_name),
                "tamil_name": crop_hint(crop_name, "ta"),
                "price_band": band["label"],
                "price_band_key": band["key"],
                "source": "excel",
                "is_farmer_listing": False,
            }
        )
        if limit is not None and len(items) >= limit:
            break
    return items


def fetch_external_market_data(query=""):
    if not settings.ENAM_MARKET_API_URL:
        return None
    endpoint = _resolve_api_url(settings.ENAM_MARKET_API_URL, settings.UMANG_API_BASE_URL)
    param_sets = [
        {"api-key": settings.DATA_GOV_API_KEY, "q": query},
        {"api-key": settings.DATA_GOV_API_KEY, "keyword": query},
        {"api-key": settings.DATA_GOV_API_KEY, "search": query},
        {"apikey": settings.DATA_GOV_API_KEY, "q": query},
        {"apiKey": settings.DATA_GOV_API_KEY, "q": query},
        {"api-key": settings.DATA_GOV_API_KEY},
    ]
    if not query:
        param_sets = [{"api-key": settings.DATA_GOV_API_KEY}]
    header_sets = [
        {},
        {"x-api-key": settings.DATA_GOV_API_KEY},
        {"api-key": settings.DATA_GOV_API_KEY},
        {"Authorization": settings.DATA_GOV_API_KEY},
    ]
    payload = _fetch_json_variants(endpoint, param_sets=param_sets, header_sets=header_sets)
    records = _extract_records(payload)
    items = []
    for record in records:
        crop_name = str(
            record.get("crop_name")
            or record.get("commodity")
            or record.get("Commodity")
            or record.get("name")
            or "Crop"
        )
        location = str(
            record.get("location")
            or record.get("market")
            or record.get("Market")
            or record.get("district")
            or record.get("state")
            or "Market"
        )
        price = record.get("modal_price") or record.get("price") or record.get("Modal_Price") or 0
        band = price_band(float(price or 0))
        items.append(
            {
                "crop_name": crop_name,
                "quantity": record.get("quantity") or record.get("arrival_qty") or 0,
                "unit": record.get("unit") or "kg",
                "location": location,
                "expected_price": float(price or 0),
                "contact": record.get("contact") or "Market feed",
                "description": record.get("variety") or record.get("remarks") or "Live market update",
                "updated": str(record.get("updated_at") or record.get("date") or timezone.now().strftime("%d %b %Y %I:%M %p")),
                "image_url": crop_image(crop_name),
                "image_hint": crop_hint(crop_name),
                "tamil_name": crop_hint(crop_name, "ta"),
                "price_band": band["label"],
                "price_band_key": band["key"],
                "source": "external",
                "is_farmer_listing": False,
            }
        )
    return items


def get_realtime_market_data(query=""):
    if not settings.ENAM_MARKET_API_URL:
        return {"items": [], "status": "disabled", "fetched_at": None}
    try:
        items = fetch_external_market_data(query) or []
        return _cache_payload("market", items, query=query)
    except Exception:
        cached = _cached_payload("market", query=query)
        if cached:
            cached["status"] = "cached"
            return cached
        return {"items": [], "status": "offline", "fetched_at": None}


def fetch_external_storage_data(query="", lat=None, lng=None):
    if not settings.GODOWN_API_URL:
        return None
    endpoint = _resolve_api_url(settings.GODOWN_API_URL, settings.DATA_GOV_API_BASE_URL)
    base_params = {
        "api-key": settings.DATA_GOV_API_KEY,
        "format": "json",
        "limit": 50,
        "offset": 0,
    }
    param_sets = [base_params]
    if query:
        param_sets = [
            {**base_params, "q": query},
            {**base_params, "filters[district]": query},
            {**base_params, "filters[state]": query},
            base_params,
        ]
    payload = _fetch_json_variants(endpoint, param_sets=param_sets)
    records = _extract_records(payload)
    items = []
    for record in records:
        name_en = str(
            record.get("warehouse_name")
            or record.get("godown_name")
            or record.get("name")
            or record.get("warehouse")
            or "Warehouse"
        )
        item = {
            "name_en": name_en,
            "name_ta": str(record.get("name_ta") or name_en),
            "district": str(record.get("district") or record.get("location") or record.get("state") or "District"),
            "scheme_name": str(record.get("scheme_name") or record.get("scheme") or record.get("warehouse_type") or record.get("category") or "Government Warehouse"),
            "available_tons": int(float(record.get("available_tons") or record.get("available_capacity") or 0)),
            "capacity_tons": int(float(record.get("capacity_tons") or record.get("capacity") or 0)),
            "contact_number": str(record.get("contact_number") or record.get("phone") or "N/A"),
            "distance_km": None,
            "image_url": WAREHOUSE_DEFAULT_IMAGE,
            "source": "external",
            "warehouse_source": "external",
        }
        try:
            warehouse_lat = float(record.get("latitude"))
            warehouse_lng = float(record.get("longitude"))
            if lat is not None and lng is not None:
                item["distance_km"] = round(haversine_km(float(lat), float(lng), warehouse_lat, warehouse_lng), 1)
        except (TypeError, ValueError):
            pass
        items.append(item)
    return items


def get_realtime_storage_data(query="", lat=None, lng=None):
    if not settings.GODOWN_API_URL:
        return {"items": [], "status": "disabled", "fetched_at": None}
    try:
        items = fetch_external_storage_data(query, lat=lat, lng=lng) or []
        return _cache_payload("storage", items, query=query, lat=lat, lng=lng)
    except Exception:
        cached = _cached_payload("storage", query=query, lat=lat, lng=lng)
        if cached:
            cached["status"] = "cached"
            return cached
        return {"items": [], "status": "offline", "fetched_at": None}


def send_sms_notification(user, phone, message_text):
    """Send SMS notification to user and log it."""
    from .models import SMSLog
    sms_log = SMSLog.objects.create(
        user=user,
        phone=phone,
        message=message_text,
        status="pending"
    )
    
    provider = settings.SMS_PROVIDER
    
    if provider == "twilio":
        try:
            from twilio.rest import Client
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            response = client.messages.create(
                body=message_text,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=phone,
            )
            sms_log.external_id = response.sid
            sms_log.status = "sent"
            sms_log.sent_at = timezone.now()
            sms_log.save()
            return True
        except Exception as e:
            sms_log.status = "failed"
            sms_log.error_message = str(e)
            sms_log.save()
            return False
    else:
        print(f"[SMS Demo to {phone}] {message_text}")
        sms_log.status = "sent"
        sms_log.sent_at = timezone.now()
        sms_log.save()
        return True


def send_notification_with_sms(
    user,
    notification_type,
    title,
    message_text,
    related_booking=None,
    related_purchase=None,
):
    """Create notification and optionally send SMS."""
    from .models import Notification
    
    notification = Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message_text,
        related_booking=related_booking,
        related_purchase=related_purchase,
    )
    if user.phone:
        sms_text = f"{title}: {message_text[:100]}"
        if send_sms_notification(user, user.phone, sms_text):
            notification.is_sent_sms = True
            notification.save()
    write_mongo_event(
        "notifications",
        {
            "user_id": user.id,
            "notification_type": notification_type,
            "title": title,
            "message": message_text,
            "sent_sms": notification.is_sent_sms,
            "created_at": timezone.now(),
        },
    )
    
    return notification


def initiate_ivr_call(user, phone, twiml_url_template=""):
    """Initiate an IVR call using Twilio."""
    from .models import IVRCall
    call_id = f"ivr_{user.id}_{timezone.now().timestamp()}"
    ivr_call = IVRCall.objects.create(
        user=user,
        phone=phone,
        call_id=call_id,
        status="initiated",
    )
    twiml_url = twiml_url_template.format(call_id=call_id) if twiml_url_template else ""
    
    if settings.SMS_PROVIDER != "twilio":
        ivr_call.transcript = "Demo IVR mode. Configure Twilio to place live calls."
        ivr_call.action_taken = "Demo IVR requested"
        ivr_call.save(update_fields=["transcript", "action_taken"])
        write_mongo_event(
            "ivr_requests",
            {
                "user_id": user.id,
                "phone": phone,
                "call_id": call_id,
                "status": "demo",
                "created_at": timezone.now(),
            },
        )
        return ivr_call

    try:
        from twilio.rest import Client

        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.calls.create(
            to=phone,
            from_=settings.TWILIO_PHONE_NUMBER,
            url=twiml_url,
        )
        write_mongo_event(
            "ivr_requests",
            {
                "user_id": user.id,
                "phone": phone,
                "call_id": call_id,
                "status": "initiated",
                "created_at": timezone.now(),
            },
        )
        return ivr_call
    except Exception as e:
        ivr_call.status = "failed"
        ivr_call.transcript = str(e)
        ivr_call.save(update_fields=["status", "transcript"])
        print(f"IVR Call initiation failed: {e}")
        return None


def calculate_user_rating(user):
    """Calculate average rating for a user."""
    from django.db.models import Avg
    from .models import Review
    
    avg_rating = Review.objects.filter(
        reviewed_user=user
    ).aggregate(avg_rating=Avg('rating'))['avg_rating']
    
    return round(avg_rating, 2) if avg_rating else 0.0


def get_warehouse_rating(warehouse):
    """Get average rating for a warehouse."""
    from django.db.models import Avg
    from .models import Review
    
    avg_rating = Review.objects.filter(
        reviewed_warehouse=warehouse
    ).aggregate(avg_rating=Avg('rating'))['avg_rating']
    
    return round(avg_rating, 2) if avg_rating else 0.0
