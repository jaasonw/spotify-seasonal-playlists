from datetime import timezone as tz
from datetime import datetime as dt
from auth_token import sp

# returns a list of song ids
def get_unadded_songs(dt_threshold):
    song_ids = []
    chunks, offset = 20, 0                    
    while True:
        songs_liked = sp.current_user_saved_tracks(chunks, offset) # need to determine how many songs to get
        for song in songs_liked['items']:
            if dt_threshold < dt.strptime(song['added_at'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=tz.utc):
                song_ids.append(song['track']['id'])
            else: 
                return song_ids
        offset += chunks


