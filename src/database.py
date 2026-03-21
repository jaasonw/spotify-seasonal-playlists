import requests
import time
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
