from spotipy import CacheHandler
import requests
from database import pocketbase_auth
from config import pocketbase_url


class DatabaseCacheHandler(CacheHandler):
    """
    Cache handler that uses pocketbase for token data
    """

    def __init__(self, username):
        self.username = username

    def get_cached_token(self):
        token = pocketbase_auth()
        req = requests.get(
            f"{pocketbase_url}/api/collections/tokens/records?filter=(user_id=%27{self.username}%27)",
            params={"perPage": 1},
            headers={"Authorization": f"Bearer {token}"},
        )
        req.raise_for_status()
        return req.json()["items"][0]

    def save_token_to_cache(self, token_info):
        try:
            token = pocketbase_auth()
            auth_token = self.get_cached_token()
            record_id = auth_token["id"]
            req = requests.patch(
                f"{pocketbase_url}/api/collections/users/records/{record_id}",
                headers={"Authorization": f"Bearer {token}"},
                json=token_info,
            )
            req.raise_for_status()

        except Exception as e:
            print(f"Could not save token to db: ${e}")
