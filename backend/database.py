import requests
from backend.config import pocketbase_url, pocketbase_username, pocketbase_password


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


def add_user(id):
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


def add_error(id, error):
    token = pocketbase_auth()
    req = requests.post(
        f"{pocketbase_url}/api/collections/errors/records",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "user_id": id,
            "error": error,
        },
    )
    req.raise_for_status()


def remove_user(id):
    update_user(id, "active", False)
