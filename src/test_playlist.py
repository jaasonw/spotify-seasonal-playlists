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

import constant
from playlist import get_current_season, start_season_time


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


if __name__ == "__main__":
    unittest.main()
