import os
import sqlite3
from DatabaseCacheHandler import DatabaseCacheHandler
from constant import CACHE_PATH, DATABASE_NAME
import json

if __name__ == "__main__":
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    conn.execute(''' CREATE TABLE IF NOT EXISTS Tokens (
        id text,
        access_token text,
        token_type text,
        expires_in integer,
        refresh_token text,
        scope text,
        expires_at integer
    )''')
    conn.close()

    for filename in os.listdir(CACHE_PATH):
        id = filename[len(".cache-"):]
        cache_path = CACHE_PATH + "/.cache-" + id
        with open(f'{CACHE_PATH}/{filename}') as f:
            data = json.loads(f.read())
            cache_handler = DatabaseCacheHandler(id)
            cache_handler.save_token_to_cache(data)
            print([id, *data.values()])
