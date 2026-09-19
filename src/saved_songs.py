from collections import deque
from datetime import datetime as dt
from datetime import timezone as tz

import spotipy


def get_unadded_songs(dt_threshold: dt, client: spotipy.Spotify, before: dt) -> deque:
    """
    Return (liked time, track ID) pairs in the half-open checkpoint window.
    """
    song_ids = deque()
    chunks, offset = 50, 0
    while True:
        songs_liked = client.current_user_saved_tracks(chunks, offset)
        for song in songs_liked["items"]:
            added_at = dt.strptime(song["added_at"], "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=tz.utc
            )
            if added_at < dt_threshold:
                return song_ids
            if added_at < before:
                song_ids.append((added_at, song["track"]["id"]))
        # edge case: user has less liked songs than the chunk size
        if len(songs_liked["items"]) < chunks:
            return song_ids
        offset += chunks
