import os
import unittest

# config.py reads these from the environment at import time
os.environ.setdefault("client_id", "test")
os.environ.setdefault("client_secret", "test")
os.environ.setdefault("redirect_uri", "test")
os.environ.setdefault("port", "5000")
os.environ.setdefault("pocketbase_url", "test")
os.environ.setdefault("pocketbase_username", "test")
os.environ.setdefault("pocketbase_password", "test")

from app import is_transient_error


class TestIsTransientError(unittest.TestCase):
    def test_matches_known_transient_markers(self):
        self.assertTrue(is_transient_error(Exception("Read timed out")))
        self.assertTrue(is_transient_error(Exception("HTTP 429 Too Many Requests")))
        self.assertTrue(is_transient_error(Exception("502 Bad Gateway")))

    def test_does_not_match_user_error(self):
        self.assertFalse(is_transient_error(Exception("Invalid refresh token")))
        self.assertFalse(is_transient_error(Exception("KeyError: 'user_id'")))

    def test_no_false_positive_on_empty_message(self):
        self.assertFalse(is_transient_error(Exception()))


if __name__ == "__main__":
    unittest.main()
