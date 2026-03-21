import requests
import time
from datetime import datetime as dt, timedelta
from datetime import timezone as tz
from config import pocketbase_url, pocketbase_username, pocketbase_password

# Cache for PocketBase token
_pb_token = None
_pb_token_expiry = 0
TOKEN_LIFETIME = 3600  # 1 hour in seconds


def pocketbase_auth():
    global _pb_token, _pb_token_expiry
    
    # Return cached token if still valid (with 60s buffer)
    if _pb_token and time.time() < _pb_token_expiry - 60:
        return _pb_token
        
    req = requests.post(
        f"{pocketbase_url}/api/admins/auth-with-password",
        json={"identity": pocketbase_username, "password": pocketbase_password},
    )
    req.raise_for_status()
    _pb_token = req.json()["token"]
    # PocketBase tokens are usually valid for 14 days, but let's refresh hourly to be safe
    # and avoid checking "exp" claim decoding complexity
    _pb_token_expiry = time.time() + TOKEN_LIFETIME
    
    return _pb_token


def get_user(id):
    token = pocketbase_auth()
    req = requests.get(
        f"{pocketbase_url}/api/collections/users/records?filter=(user_id=%27{id}%27)",
        params={"perPage": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    req.raise_for_status()
    return req.json()["items"][0]


def get_users():
    # TODO: pagination if we ever have that many users but for now we dont
    # and i am lazy
    token = pocketbase_auth()
    req = requests.get(
        f"{pocketbase_url}/api/collections/users/records",
        params={"perPage": 500},
        headers={"Authorization": f"Bearer {token}"},
    )
    req.raise_for_status()
    return req.json()["items"]


def get_active_user_count():
    """
    Get the total number of active users.
    """
    token = pocketbase_auth()
    try:
        req = requests.get(
            f"{pocketbase_url}/api/collections/users/records",
            params={
                "perPage": 1,
                "filter": "active=true",
                "fields": "id",  # Optimize: only fetch ID
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        req.raise_for_status()
        return req.json()["totalItems"]
    except Exception:
        return 0


def get_users_needing_update(update_frequency=300, limit=1):
    """
    Get active users who haven't been updated recently.
    Returns list of users sorted by last_update (oldest first).
    """
    token = pocketbase_auth()
    
    # We fetch active users and filter in Python for robustness with date formats
    # This is fine for < 500 users. For larger scale, we'd use PocketBase filtering.
    try:
        req = requests.get(
            f"{pocketbase_url}/api/collections/users/records",
            # We filter for active users directly in PocketBase if possible
            # PB filter syntax: filter=(active=true)
            params={
                "perPage": 500,
                "filter": "active=true",
                "sort": "updated", 
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        req.raise_for_status()
        all_active_users = req.json()["items"]
    except Exception:
        # Fallback to getting all users if filter fails
        all_active_users = [u for u in get_users() if u.get("active")]

    # Calculate cutoff time (UTC)
    cutoff_time = dt.now(tz=tz.utc) - timedelta(seconds=update_frequency)
    stale_users = []
    
    for user in all_active_users:
        # Check last_polled (scheduler timestamp) instead of last_update (content timestamp)
        last_polled_str = user.get("last_polled", "")
        
        # If never polled, it's stale
        if not last_polled_str:
            stale_users.append(user)
            continue
            
        try:
            # Parse "YYYY-MM-DD HH:MM:SS"
            last_polled = dt.strptime(last_polled_str, "%Y-%m-%d %H:%M:%S")
            # Force UTC if naive
            if not last_polled.tzinfo:
                last_polled = last_polled.replace(tzinfo=tz.utc)
                
            if last_polled < cutoff_time:
                stale_users.append(user)
        except ValueError:
            # If date parsing fails, treat as stale
            stale_users.append(user)
            
    # Sort by last_polled string (oldest first)
    stale_users.sort(key=lambda u: u.get("last_polled", ""))
    
    return stale_users[:limit]


def update_user(id, field, value, user_record=None):
    token = pocketbase_auth()
    
    # Use provided record if available to avoid extra fetch
    if user_record:
        record_id = user_record["id"]
    else:
        user = get_user(id)
        record_id = user["id"]
        
    req = requests.patch(
        f"{pocketbase_url}/api/collections/users/records/{record_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={field: value},
    )
    req.raise_for_status()


def increment_field(id, field):
    user = get_user(id)
    entry = user.get(field, 0)  # Default to 0 if field missing
    update_user(id, field, entry + 1, user_record=user)


def get_or_create_user(id):
    """Get user if exists, create if not. Returns the user record."""
    try:
        user = get_user(id)
        # Reactivate if they're logging in again after deactivating
        if not user.get("active", True):
            update_user(id, "active", True, user_record=user)
            user["active"] = True  # Update local object
            return user
        return user
    except (IndexError, KeyError):
        # User doesn't exist, create them
        token = pocketbase_auth()
        req = requests.post(
            f"{pocketbase_url}/api/collections/users/records",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "user_id": id,
                "update_count": 0,
                "error_count": 0,
                "last_error": "",
                "last_playlist": "",
                "last_update": "",
                "last_polled": "",
                "active": True,
            },
        )
        req.raise_for_status()
        return get_user(id)


def add_error(id, error, traceback):
    token = pocketbase_auth()
    req = requests.post(
        f"{pocketbase_url}/api/collections/errors/records",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "user_id": id,
            "error": error,
            "traceback": traceback,
        },
    )
    req.raise_for_status()


def remove_user(id):
    update_user(id, "active", False)


def get_recent_errors(limit=50):
    """Get recent errors from the database, sorted by newest first"""
    token = pocketbase_auth()
    req = requests.get(
        f"{pocketbase_url}/api/collections/errors/records",
        params={"perPage": limit, "sort": "-created"},
        headers={"Authorization": f"Bearer {token}"},
    )
    req.raise_for_status()
    return req.json()["items"]


def update_heartbeat(component, status, details=""):
    """
    Updates the system_status collection with a heartbeat.
    """
    token = pocketbase_auth()
    timestamp = dt.now(tz=tz.utc).strftime("%Y-%m-%d %H:%M:%S")
    
    # Check if record exists
    try:
        req = requests.get(
            f"{pocketbase_url}/api/collections/system_status/records",
            params={"filter": f"component='{component}'"},
            headers={"Authorization": f"Bearer {token}"},
        )
        req.raise_for_status()
        items = req.json()["items"]
        
        if items:
            # Update existing
            record_id = items[0]["id"]
            req = requests.patch(
                f"{pocketbase_url}/api/collections/system_status/records/{record_id}",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "last_heartbeat": timestamp,
                    "status": status,
                    "details": details
                },
            )
        else:
            # Create new
            req = requests.post(
                f"{pocketbase_url}/api/collections/system_status/records",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "component": component,
                    "last_heartbeat": timestamp,
                    "status": status,
                    "details": details
                },
            )
        req.raise_for_status()
    except Exception as e:
        print(f"Failed to update heartbeat: {e}")


def get_worker_status():
    """
    Get the latest worker status.
    """
    try:
        token = pocketbase_auth()
        req = requests.get(
            f"{pocketbase_url}/api/collections/system_status/records",
            params={"filter": "component='worker'", "sort": "-last_heartbeat"},
            headers={"Authorization": f"Bearer {token}"},
        )
        req.raise_for_status()
        items = req.json()["items"]
        return items[0] if items else None
    except Exception:
        return None
