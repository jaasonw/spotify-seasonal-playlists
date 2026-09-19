from datetime import datetime as dt
from datetime import timezone as tz
from itertools import groupby

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
        description="AUTOMATED PLAYLIST - https://physicsbirds.com/spotify",
    )
    return resp["id"]


def get_target_playlist(date: dt, client: spotipy.Spotify, user) -> str:
    """
    Returns the playlist id based on date, creating the playlist if needed.

    Relies on the cached last_playlist id; we never look a playlist up by name.
    """
    # december of 2019 looks for playlist "winter 2020"
    target_playlist_name = (
        get_current_season(date)
        + " "
        + str(date.year if date.month != 12 else date.year + 1)
    )

    # case 1: Playlist is cached and playlist is current season
    #   Good, use it
    # case 2: Playlist is cached but playlist is out of season
    #   Make a new playlist and cache it
    # case 3: Playlist isnt cached
    #   Make a new playlist and cache it
    # case 4: Playlist is cached but the user deleted it
    #   Make a new playlist and cache it

    # case 3: used to scan every playlist for a name match, but that
    # rate-limited us on large libraries. Worst case now is one duplicate
    # seasonal playlist if a record was reset, and last_playlist is rewritten
    # each run.
    playlist_id = user.get("last_playlist", "")
    if not playlist_id:
        return create_playlist(client, target_playlist_name)

    try:
        # case 1
        if client.playlist(playlist_id)["name"] == target_playlist_name:
            return playlist_id
    except spotipy.SpotifyException as e:
        # case 4: make a new one rather than erroring every cycle until the
        # user trips ERROR_THRESHOLD and gets marked inactive
        if e.http_status != 404:
            raise

    # case 2
    return create_playlist(client, target_playlist_name)


def get_newest_date_in_playlist(pl_id: int, client: spotipy.Spotify):
    """
    returns a datetime object of the most recently added song of a playlist

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


def update_playlist(client: spotipy.Spotify, user):
    """
    Updates the playlist for a specific client

    client: the client to update
    """
    # Exclude this second: likes arriving during the fetch belong to the next run.
    cutoff = dt.now(tz=tz.utc).replace(microsecond=0)
    last_updated = (
        dt.strptime(user["last_update"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=tz.utc)
        if user["last_update"] != ""
        else start_season_time(cutoff)
    )
    songs = sorted(get_unadded_songs(last_updated, client, cutoff))
    seasons = {
        season: [track_id for _, track_id in tracks]
        for season, tracks in groupby(
            songs, key=lambda song: start_season_time(song[0])
        )
    }
    seasons.setdefault(start_season_time(cutoff), [])
    user = dict(user)
    for season, track_ids in seasons.items():
        target_playlist = get_target_playlist(season, client, user)
        # Save the destination before writing tracks so a retry reuses it.
        database.update_user(
            user["user_id"], "last_playlist", target_playlist, user_record=user
        )
        user["last_playlist"] = target_playlist

        if track_ids:
            # Reconcile partial batches and requests that succeeded before a timeout.
            existing = set()
            offset = 0
            while True:
                page = client.playlist_items(target_playlist, limit=100, offset=offset)
                for item in page["items"]:
                    track = item.get("track")
                    if track:
                        existing.add(track.get("id"))
                if not page.get("next"):
                    break
                offset += len(page["items"])
            missing = list(dict.fromkeys(t for t in track_ids if t not in existing))
            for offset in range(0, len(missing), constant.SPOTIFY_ADD_TRACKS_LIMIT):
                client.user_playlist_add_tracks(
                    user["user_id"],
                    target_playlist,
                    missing[offset : offset + constant.SPOTIFY_ADD_TRACKS_LIMIT],
                )

        next_season = dt(
            season.year + (season.month == 12),
            season.month % 12 + 3,
            1,
            tzinfo=tz.utc,
        )
        checkpoint = min(next_season, cutoff).strftime("%Y-%m-%d %H:%M:%S")
        database.update_user(
            user["user_id"], "last_update", checkpoint, user_record=user
        )
    if songs:
        database.increment_field(user["user_id"], "update_count")
