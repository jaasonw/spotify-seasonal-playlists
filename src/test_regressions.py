import os
import unittest
from concurrent.futures import Future
from datetime import datetime, timezone
from unittest.mock import Mock, patch

for key in (
    "client_id",
    "client_secret",
    "redirect_uri",
    "port",
    "pocketbase_url",
    "pocketbase_username",
    "pocketbase_password",
    "FLASK_SECRET_KEY",
):
    os.environ.setdefault(key, "test")

import app
import playlist
import web_auth
from saved_songs import get_unadded_songs


class FixedTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)


def liked(track_id, added_at):
    return {"track": {"id": track_id}, "added_at": added_at}


class TestSyncRegression(unittest.TestCase):
    def setUp(self):
        self.user = {
            "id": "record",
            "user_id": "someone",
            "last_playlist": "fall 2026",
            "last_update": "2026-09-01 00:00:00",
        }
        self.tracks = {"fall 2026": []}
        self.saved = []
        self.client = Mock()
        self.client.me.return_value = {"id": "someone"}
        self.client.playlist.side_effect = lambda pid: {"name": pid}
        self.client.user_playlist_create.side_effect = self.create
        self.client.current_user_saved_tracks.side_effect = lambda limit, offset: {
            "items": self.saved[offset : offset + limit]
        }
        self.client.playlist_items.side_effect = self.items
        self.client.user_playlist_add_tracks.side_effect = self.add
        self.enterContext(patch.object(playlist, "dt", FixedTime))
        self.enterContext(
            patch.object(playlist.database, "update_user", side_effect=self.write)
        )
        self.count = self.enterContext(
            patch.object(playlist.database, "increment_field")
        )

    def write(self, user_id, field, value, user_record=None):
        self.user[field] = value

    def create(self, user_id, name, **kwargs):
        self.tracks[name] = []
        return {"id": name}

    def items(self, pid, limit, offset):
        tracks = self.tracks[pid]
        return {
            "items": [{"track": {"id": t}} for t in tracks[offset : offset + limit]],
            "next": offset + limit < len(tracks),
        }

    def add(self, user_id, pid, tracks):
        self.tracks[pid].extend(tracks)

    def test_failure_does_not_advance_checkpoint(self):
        self.saved = [liked("a", "2026-09-17T00:00:00Z")]
        self.client.user_playlist_add_tracks.side_effect = RuntimeError("failed")
        with self.assertRaises(RuntimeError):
            playlist.update_playlist(self.client, self.user)
        self.assertEqual(self.user["last_update"], "2026-09-01 00:00:00")
        self.count.assert_not_called()

    def test_partial_batch_retry_does_not_duplicate_successful_tracks(self):
        self.saved = [liked(str(i), "2026-09-17T00:00:00Z") for i in range(101)]
        calls = 0

        def fail_second(user_id, pid, tracks):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("failed")
            self.add(user_id, pid, tracks)

        self.client.user_playlist_add_tracks.side_effect = fail_second
        with self.assertRaises(RuntimeError):
            playlist.update_playlist(self.client, self.user)
        self.assertEqual(len(self.tracks["fall 2026"]), 100)
        self.client.user_playlist_add_tracks.side_effect = self.add
        playlist.update_playlist(self.client, self.user)
        self.assertEqual(len(self.tracks["fall 2026"]), 101)
        self.assertEqual(len(set(self.tracks["fall 2026"])), 101)
        self.assertEqual(self.user["last_update"], "2026-09-18 12:00:00")

    def test_timeout_after_success_is_reconciled(self):
        self.saved = [liked("a", "2026-09-17T00:00:00Z")]

        def ambiguous_add(user_id, pid, tracks):
            self.add(user_id, pid, tracks)
            raise TimeoutError()

        self.client.user_playlist_add_tracks.side_effect = ambiguous_add
        with self.assertRaises(TimeoutError):
            playlist.update_playlist(self.client, self.user)
        self.client.user_playlist_add_tracks.side_effect = self.add
        playlist.update_playlist(self.client, self.user)
        self.assertEqual(self.tracks["fall 2026"], ["a"])

    def test_backlog_is_routed_by_liked_season(self):
        self.user.update(last_playlist="summer 2026", last_update="2026-08-01 00:00:00")
        self.tracks["summer 2026"] = []
        self.saved = [
            liked("fall", "2026-09-01T00:00:00Z"),
            liked("summer", "2026-08-31T23:59:59Z"),
        ]
        playlist.update_playlist(self.client, self.user)
        self.assertEqual(self.tracks["summer 2026"], ["summer"])
        self.assertEqual(self.tracks["fall 2026"], ["fall"])
        self.assertEqual(self.user["last_playlist"], "fall 2026")

    def test_failed_later_season_preserves_completed_season(self):
        self.user.update(last_playlist="summer 2026", last_update="2026-08-01 00:00:00")
        self.tracks["summer 2026"] = []
        self.saved = [
            liked("fall", "2026-09-01T00:00:00Z"),
            liked("summer", "2026-08-31T23:59:59Z"),
        ]

        def fail_fall(user_id, pid, tracks):
            if pid == "fall 2026":
                raise RuntimeError()
            self.add(user_id, pid, tracks)

        self.client.user_playlist_add_tracks.side_effect = fail_fall
        with self.assertRaises(RuntimeError):
            playlist.update_playlist(self.client, self.user)
        self.assertEqual(self.user["last_update"], "2026-09-01 00:00:00")
        self.client.user_playlist_add_tracks.side_effect = self.add
        playlist.update_playlist(self.client, self.user)
        self.assertEqual(self.tracks["summer 2026"], ["summer"])
        self.assertEqual(self.tracks["fall 2026"], ["fall"])

    def test_fetch_window_includes_lower_boundary_and_defers_current_second(self):
        self.saved = [
            liked("during-fetch", "2026-09-18T12:00:01Z"),
            liked("current-second", "2026-09-18T12:00:00Z"),
            liked("boundary", "2026-09-01T00:00:00Z"),
        ]
        playlist.update_playlist(self.client, self.user)
        self.assertEqual(self.tracks["fall 2026"], ["boundary"])
        with patch.object(
            FixedTime,
            "now",
            return_value=datetime(2026, 9, 18, 12, 0, 2, tzinfo=timezone.utc),
        ):
            playlist.update_playlist(self.client, self.user)
        self.assertEqual(
            self.tracks["fall 2026"], ["boundary", "current-second", "during-fetch"]
        )

    def test_saved_tracks_pagination(self):
        self.saved = [liked(str(i), "2026-09-17T00:00:00Z") for i in range(51)]
        result = get_unadded_songs(
            datetime(2026, 9, 1, tzinfo=timezone.utc), self.client, FixedTime.now()
        )
        self.assertEqual(len(result), 51)
        self.assertEqual(self.client.current_user_saved_tracks.call_count, 2)

    def test_existing_playlist_pagination_prevents_duplicates(self):
        self.tracks["fall 2026"] = [str(i) for i in range(101)]
        self.saved = [liked("100", "2026-09-17T00:00:00Z")]
        playlist.update_playlist(self.client, self.user)
        self.assertEqual(self.client.playlist_items.call_count, 2)
        self.client.user_playlist_add_tracks.assert_not_called()

    def test_winter_backlog_uses_following_year_and_retries_new_destination(self):
        self.user.update(last_playlist="fall 2025", last_update="2025-11-30 00:00:00")
        self.tracks["fall 2025"] = []
        self.saved = [liked("winter", "2025-12-01T00:00:00Z")]
        self.client.user_playlist_add_tracks.side_effect = RuntimeError()
        with self.assertRaises(RuntimeError):
            playlist.update_playlist(self.client, self.user)
        self.assertEqual(self.user["last_playlist"], "winter 2026")
        self.client.user_playlist_add_tracks.side_effect = self.add
        playlist.update_playlist(self.client, self.user)
        self.assertEqual(self.tracks["winter 2026"], ["winter"])
        created = [
            call.args[1] for call in self.client.user_playlist_create.call_args_list
        ]
        self.assertEqual(created.count("winter 2026"), 1)


class TestWebRegression(unittest.TestCase):
    def setUp(self):
        self.browser = web_auth.auth_server.test_client()
        self.oauth = self.enterContext(patch.object(web_auth, "SpotifyOAuth"))
        self.oauth.return_value.get_authorize_url.return_value = (
            "https://example.test/auth"
        )

    def test_init_removed(self):
        self.assertEqual(self.browser.get("/init?id=someone").status_code, 404)

    def test_login_generates_session_bound_state(self):
        self.assertEqual(self.browser.get("/login").status_code, 302)
        with self.browser.session_transaction() as session:
            state = session["oauth_state"]
        self.assertGreaterEqual(len(state), 32)
        self.oauth.return_value.get_authorize_url.assert_called_once_with(state=state)

    def test_missing_and_mismatched_state_rejected_before_exchange(self):
        self.assertEqual(self.browser.get("/login?code=code").status_code, 400)
        with self.browser.session_transaction() as session:
            session["oauth_state"] = "expected"
        self.assertEqual(
            self.browser.get("/login?code=code&state=wrong").status_code, 400
        )
        self.oauth.return_value.get_access_token.assert_not_called()

    def test_valid_state_is_single_use_and_login_does_not_update_playlists(self):
        with self.browser.session_transaction() as session:
            session["oauth_state"] = "expected"
        with (
            patch.object(web_auth.spotipy, "Spotify") as client,
            patch.object(
                web_auth.database,
                "get_or_create_user",
                return_value={"user_id": "someone"},
            ),
            patch.object(web_auth, "DatabaseCacheHandler"),
        ):
            client.return_value.me.return_value = {"id": "someone"}
            self.assertEqual(
                self.browser.get("/login?code=code&state=expected").status_code, 302
            )
            client.return_value.user_playlist_add_tracks.assert_not_called()
        with self.browser.session_transaction() as session:
            self.assertEqual(session["user_id"], "someone")
            self.assertNotIn("oauth_state", session)
        self.assertEqual(
            self.browser.get("/login?code=code&state=expected").status_code, 400
        )
        self.oauth.return_value.get_access_token.assert_called_once()


class StopLoop(BaseException):
    pass


class TestWorkerRegression(unittest.TestCase):
    def test_completed_user_can_be_scheduled_again(self):
        future = Future()
        sleeps = 0

        def sleep(_):
            nonlocal sleeps
            sleeps += 1
            if sleeps == 1:
                future.set_result(None)
            else:
                raise StopLoop()

        with (
            patch.object(app, "ThreadPoolExecutor") as pool,
            patch.object(app.db, "update_heartbeat"),
            patch.object(app.db, "get_active_user_count", return_value=1),
            patch.object(
                app.db,
                "get_users_needing_update",
                return_value=[{"user_id": "someone"}],
            ),
            patch.object(app.time, "sleep", side_effect=sleep),
        ):
            executor = pool.return_value.__enter__.return_value
            executor.submit.return_value = future
            with self.assertRaises(StopLoop):
                app.run_worker_loop(60)
            self.assertEqual(executor.submit.call_count, 2)

    def test_pending_users_are_not_resubmitted_and_capacity_is_bounded(self):
        users = [{"user_id": str(i)} for i in range(10)]
        with (
            patch.object(app, "ThreadPoolExecutor") as pool,
            patch.object(app.db, "update_heartbeat"),
            patch.object(app.db, "get_active_user_count", return_value=10),
            patch.object(app.db, "get_users_needing_update", return_value=users),
            patch.object(app.time, "sleep", side_effect=[None, StopLoop()]),
        ):
            executor = pool.return_value.__enter__.return_value
            executor.submit.side_effect = lambda *args: Future()
            with self.assertRaises(StopLoop):
                app.run_worker_loop(60)
            self.assertEqual(executor.submit.call_count, app.constant.MAX_WORKERS)
            submitted = [
                call.args[1]["user_id"] for call in executor.submit.call_args_list
            ]
            self.assertEqual(len(submitted), len(set(submitted)))


if __name__ == "__main__":
    unittest.main()
