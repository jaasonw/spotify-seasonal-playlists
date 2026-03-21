from collections import deque
from datetime import datetime as dt
from datetime import timezone as tz

import spotipy


# returns a list of song ids
def get_unadded_songs(dt_threshold: dt, client: spotipy.Spotify) -> deque:
    """
    finds all songs that were added past the last date
    """
    song_ids = deque()
    chunks, offset = 50, 0
    while True:
        songs_liked = client.current_user_saved_tracks(chunks, offset)
        for song in songs_liked["items"]:
            added_at = dt.strptime(song["added_at"], "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=tz.utc
            )
            if dt_threshold < added_at:
                song_ids.append(song["track"]["id"])
            else:
                return song_ids
        # edge case: user has less liked songs than the chunk size
        if len(songs_liked["items"]) < chunks:
            return song_ids
        offset += chunks
