from datetime import datetime as dt
from datetime import timezone as tz

import spotipy

import constant
import database
from saved_songs import get_unadded_songs


def get_current_season(now: dt) -> str:
    """returns the season given a time"""
    if now.month > 2 and now.month < 6:  # MAR - MAY
        return constant.SPRING
    elif now.month > 5 and now.month < 9:  # JUN - AUG
        return constant.SUMMER
    elif now.month > 8 and now.month < 12:  # SEPT - NOV
        return constant.FALL
    else:  # DEC - FEB
        return constant.WINTER


def create_playlist(client: spotipy.Spotify, playlist_name: str) -> str:
    resp = client.user_playlist_create(
        client.me()["id"],
        playlist_name,
        public=False,
        description="AUTOMATED PLAYLIST - https://github.com/turrence/spotify-new-music-sorter",
    )
    return resp["id"]


def get_target_playlist(date: dt, client: spotipy.Spotify, user) -> str:
    """
    Returns the playlist id based on date

    ASSUMPTIONS: a user has no duplicate playlist names
    In the case that a user has a duplicate playlist name, the script will modify the one 'lower' in the user's playlist library
    Solution: no intuitive workaround
    """
    # december of 2019 looks for playlist "winter 2020"
    target_playlist_name = (
        get_current_season(date)
        + " "
        + str(date.year if date.month != 12 else date.year + 1)
    )
    chunk, offset = 50, 0
    all_playlists = {}

    # Case 1: Playlist is cached and playlist is current season
    #   Good, use it
    # Case 2: Playlist is cached but playlist is out of season
    #   Make a new playlist and cache it
    # Case 3: Playlist isnt cached
    #   Look for it

    playlist_id = ""
    try:
        playlist_id = user["last_playlist"]
        # case 1
        if (
            playlist_id != ""
            and client.playlist(playlist_id)["name"] == target_playlist_name
        ):
            return playlist_id
        # case 2
        else:
            return create_playlist(client, target_playlist_name)
    except KeyError as e:
        # case 3: do nothing, it's not cached, hopefully this is rare
        pass

    while True:
        playlist_info = client.current_user_playlists(chunk, offset)
        for item in playlist_info["items"]:
            all_playlists[item["name"]] = item["id"]
        if len(all_playlists) >= playlist_info["total"]:
            break
        else:
            offset += chunk

    if target_playlist_name not in all_playlists:
        return create_playlist(client, target_playlist_name)
    else:
        return all_playlists[target_playlist_name]


# returns a datetime object of the most recently added song of a playlist


def get_newest_date_in_playlist(pl_id: int, client: spotipy.Spotify):
    """
    ASSUMPTIONS: the order of the songs in the playlist is in which the songs were added
    Potential Solution: loop through every track's date added and find the max (not implemented)
    """
    songs = client.playlist_tracks(pl_id, fields="total")
    if songs["total"] == 0:
        return start_season_time(dt.now(tz=tz.utc))
    last_song = client.playlist_tracks(
        pl_id, fields="items, total", offset=songs["total"] - 1
    )
    return dt.strptime(
        last_song["items"][len(last_song["items"]) - 1]["added_at"],
        "%Y-%m-%dT%H:%M:%SZ",
    ).replace(tzinfo=tz.utc)


def start_season_time(now: dt) -> dt:
    """
    given a datetime, return a dt of the start of the season
    for e.g. if its winter 2020, return DEC 1, 2019 00:00 UTC
    for e.g. if its spring 2020, return MAR 1, 2020 00:00 UTC
    """
    if now.month in [12, 1, 2]:
        return dt(now.year if now.month == 12 else now.year - 1, 12, 1, tzinfo=tz.utc)
    elif now.month in range(3, 6):
        return dt(now.year, 3, 1, tzinfo=tz.utc)
    elif now.month in range(6, 9):
        return dt(now.year, 6, 1, tzinfo=tz.utc)
    else:
        return dt(now.year, 9, 1, tzinfo=tz.utc)


# Updates the playlist for a specific client
# client: the client to update


def update_playlist(client: spotipy.Spotify, user):
    target_playlist = get_target_playlist(dt.now(tz=tz.utc), client, user)
    # in utc
    # last_updated = get_newest_date_in_playlist(target_playlist, client)
    last_updated = (
        dt.strptime(user["last_update"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=tz.utc)
        if user["last_update"] != ""
        else start_season_time(dt.now(tz=tz.utc))
    )
    songs_to_be_added = get_unadded_songs(last_updated, client)

    database.update_user(user["user_id"], "last_playlist", target_playlist)
    if len(songs_to_be_added) < 1:
        return
    timestamp = dt.now(tz=tz.utc).strftime("%Y-%m-%d %H:%M:%S")
    database.update_user(user["user_id"], "last_update", timestamp)
    database.increment_field(user["user_id"], "update_count")

    # we can only add 100 songs at a time, place all the songs in a queue
    # and dequeue into a chunk 100 songs at a time
    chunk = []
    while songs_to_be_added:
        chunk.append(songs_to_be_added.popleft())
        if len(chunk) == 100:
            client.user_playlist_add_tracks(client.me()["id"], target_playlist, chunk)
            chunk.clear()
    # if the chunk isn't completely filled then add the rest of the songs
    if len(chunk) > 0:
        client.user_playlist_add_tracks(client.me()["id"], target_playlist, chunk)
