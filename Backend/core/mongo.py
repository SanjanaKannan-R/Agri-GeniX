from django.conf import settings

try:
    from pymongo import MongoClient
except Exception:  
    MongoClient = None


def get_mongo_db():
    if not MongoClient:
        return None

    uri = getattr(settings, "MONGO_URI", "").strip()
    name = getattr(settings, "MONGO_DB_NAME", "").strip()
    if not uri or not name:
        return None

    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=getattr(settings, "MONGO_TIMEOUT_MS", 1500))
        client.admin.command("ping")
        return client[name]
    except Exception:
        return None


def write_mongo_event(collection_name, payload):
    db = get_mongo_db()
    if db is None:
        return False
    try:
        db[collection_name].insert_one(payload)
        return True
    except Exception:
        return False
