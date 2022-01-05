from spotipy import CacheHandler
import database as db


class DatabaseCacheHandler(CacheHandler):
    """
    Cache handler that uses the sqlite database for token data
    """

    def __init__(self, username):
        self.username = username

    def get_cached_token(self):
        with db.database_connection() as conn:
            conn.row_factory = lambda c, r: dict(
                [(col[0], r[idx]) for idx, col in enumerate(c.description)])
            cursor = conn.cursor()
            try:
                cursor.execute(
                    f'SELECT * FROM Tokens WHERE id=?', (self.username,))
                tokenRow = cursor.fetchone()
            except Exception as e:
                print(f'Could not get token: ${e}')
        return tokenRow

    def save_token_to_cache(self, token_info):
        with db.database_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    f'DELETE FROM Tokens WHERE id=?', (self.username,))
                cursor.execute('INSERT INTO Tokens VALUES (?,?,?,?,?,?,?)', (
                    self.username,
                    token_info["access_token"],
                    token_info["token_type"],
                    token_info["expires_in"],
                    token_info["refresh_token"],
                    token_info["scope"],
                    token_info["expires_at"],
                ))
                conn.commit()
            except Exception as e:
                print(f'Could not save token to db: ${e}')
