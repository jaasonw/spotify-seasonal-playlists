import os
import unittest
from datetime import datetime as dt
from datetime import timezone as tz

# config.py reads these from the environment at import time
os.environ.setdefault("client_id", "test")
os.environ.setdefault("client_secret", "test")
os.environ.setdefault("redirect_uri", "test")
os.environ.setdefault("port", "5000")
os.environ.setdefault("pocketbase_url", "test")
os.environ.setdefault("pocketbase_username", "test")
os.environ.setdefault("pocketbase_password", "test")

import spotipy

import constant
from playlist import get_current_season, get_target_playlist, start_season_time


class FakeClient:
    """Stands in for spotipy.Spotify with only the methods get_target_playlist calls."""

    def __init__(self, playlists=None, raises=None):
        self.playlists = playlists or {}
        self.raises = raises
        self.created = []

    def playlist(self, playlist_id):
        if self.raises:
            raise self.raises
        return {"name": self.playlists[playlist_id]}

    def me(self):
        return {"id": "someone"}

    def user_playlist_create(self, user_id, name, public, description):
        self.created.append(name)
        return {"id": f"new-{name}"}


class TestGetCurrentSeason(unittest.TestCase):
    def test_spring_boundaries(self):
        self.assertEqual(get_current_season(dt(2024, 3, 1)), constant.SPRING)
        self.assertEqual(get_current_season(dt(2024, 5, 31)), constant.SPRING)

    def test_summer_boundaries(self):
        self.assertEqual(get_current_season(dt(2024, 6, 1)), constant.SUMMER)
        self.assertEqual(get_current_season(dt(2024, 8, 31)), constant.SUMMER)

    def test_fall_boundaries(self):
        self.assertEqual(get_current_season(dt(2024, 9, 1)), constant.FALL)
        self.assertEqual(get_current_season(dt(2024, 11, 30)), constant.FALL)

    def test_winter_boundaries(self):
        self.assertEqual(get_current_season(dt(2024, 12, 1)), constant.WINTER)
        self.assertEqual(get_current_season(dt(2024, 1, 1)), constant.WINTER)
        self.assertEqual(get_current_season(dt(2024, 2, 28)), constant.WINTER)


class TestStartSeasonTime(unittest.TestCase):
    def test_winter_in_december_stays_same_year(self):
        self.assertEqual(
            start_season_time(dt(2024, 12, 15)),
            dt(2024, 12, 1, tzinfo=tz.utc),
        )

    def test_winter_in_january_rolls_back_to_prior_december(self):
        self.assertEqual(
            start_season_time(dt(2024, 1, 15)),
            dt(2023, 12, 1, tzinfo=tz.utc),
        )

    def test_winter_in_february_rolls_back_to_prior_december(self):
        self.assertEqual(
            start_season_time(dt(2024, 2, 15)),
            dt(2023, 12, 1, tzinfo=tz.utc),
        )

    def test_spring(self):
        self.assertEqual(
            start_season_time(dt(2024, 4, 15)),
            dt(2024, 3, 1, tzinfo=tz.utc),
        )

    def test_summer(self):
        self.assertEqual(
            start_season_time(dt(2024, 7, 15)),
            dt(2024, 6, 1, tzinfo=tz.utc),
        )

    def test_fall(self):
        self.assertEqual(
            start_season_time(dt(2024, 10, 15)),
            dt(2024, 9, 1, tzinfo=tz.utc),
        )


class TestGetTargetPlaylist(unittest.TestCase):
    date = dt(2024, 10, 15)  # fall 2024

    def test_reuses_cached_playlist_in_current_season(self):
        client = FakeClient(playlists={"abc": "fall 2024"})
        result = get_target_playlist(self.date, client, {"last_playlist": "abc"})
        self.assertEqual(result, "abc")
        self.assertEqual(client.created, [])

    def test_creates_new_playlist_when_cached_one_is_out_of_season(self):
        client = FakeClient(playlists={"abc": "summer 2024"})
        result = get_target_playlist(self.date, client, {"last_playlist": "abc"})
        self.assertEqual(result, "new-fall 2024")
        self.assertEqual(client.created, ["fall 2024"])

    def test_creates_new_playlist_when_nothing_cached(self):
        client = FakeClient()
        self.assertEqual(
            get_target_playlist(self.date, client, {"last_playlist": ""}),
            "new-fall 2024",
        )
        self.assertEqual(
            get_target_playlist(self.date, client, {}),
            "new-fall 2024",
        )

    def test_creates_new_playlist_when_cached_one_was_deleted(self):
        client = FakeClient(
            raises=spotipy.SpotifyException(404, -1, "playlist not found")
        )
        result = get_target_playlist(self.date, client, {"last_playlist": "gone"})
        self.assertEqual(result, "new-fall 2024")

    def test_reraises_non_404_spotify_errors(self):
        client = FakeClient(raises=spotipy.SpotifyException(500, -1, "server error"))
        with self.assertRaises(spotipy.SpotifyException):
            get_target_playlist(self.date, client, {"last_playlist": "abc"})


if __name__ == "__main__":
    unittest.main()
