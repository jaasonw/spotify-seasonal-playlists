import requests
from config import pocketbase_url, pocketbase_username, pocketbase_password


def pocketbase_auth():
    req = requests.post(
        f"{pocketbase_url}/api/admins/auth-with-password",
        json={"identity": pocketbase_username, "password": pocketbase_password},
    )
    return req.json()["token"]


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


def update_user(id, field, value):
    token = pocketbase_auth()
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
    entry = user[field]
    update_user(id, field, entry + 1)


def get_or_create_user(id):
    """Get user if exists, create if not. Returns the user record."""
    try:
        user = get_user(id)
        # Reactivate if they're logging in again after deactivating
        if not user.get("active", True):
            update_user(id, "active", True)
            return get_user(id)
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
