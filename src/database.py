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


# def get_field(id, field):
#     with database_connection() as conn:
#         conn = sqlite3.connect(DATABASE_NAME)
#         conn.row_factory = lambda c, r: dict(
#             [(col[0], r[idx]) for idx, col in enumerate(c.description)]
#         )
#         cursor = conn.cursor()
#         sql = f"SELECT * FROM Users WHERE id = ?"
#         cursor.execute(sql, (id,))
#         entry = cursor.fetchone()
#         return entry[field]


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


# # TODO: Unit testing
# if __name__ == "__main__":
#     if len(sys.argv) >= 2:
#         if sys.argv[1] == "--test":
#             print(get_field("fi14v4phgvmdiqk3g5t7cwsvz", "last_playlist"))


# def init_database():
#     conn = sqlite3.connect(DATABASE_NAME)
#     cursor = conn.cursor()
#     cursor.execute(
#         ''' SELECT count(name) FROM sqlite_master WHERE type='table' AND name='Users' ''')
#     if cursor.fetchone()[0] == 0:
#         conn.execute(''' CREATE TABLE Users(
#             id TEXT,
#             update_count INTEGER DEFAULT 0,
#             error_count INTEGER DEFAULT 0,
#             last_error TEXT DEFAULT "",
#             last_playlist TEXT DEFAULT "",
#             last_update TEXT DEFAULT ""
#         ) ''')

#         print("Created table")
#         for filename in os.listdir(CACHE_PATH):
#             id = filename[len(".cache-"):]
#             add_user(id)

#     conn.execute(''' CREATE TABLE IF NOT EXISTS Errors (
#         id text
#             constraint Errors_Users_id_fk
#                 references Users (id),
#         error text
#     )''')
#     conn.close()
