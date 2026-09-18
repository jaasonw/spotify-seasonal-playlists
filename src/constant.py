SPRING = "spring"
SUMMER = "summer"
WINTER = "winter"
FALL = "fall"

SCOPE = "user-library-read playlist-read-private playlist-modify-private playlist-modify-public"
UPDATE_FREQUENCY = 60  # in seconds
ERROR_THRESHOLD = 30
BATCH_SIZE = 5
MAX_WORKERS = 5

# Markers of transient/upstream errors (Spotify API outage, rate limiting, etc.)
# that should NOT count against a user's error_count, since they aren't the
# user's fault and shouldn't lead to their account being disabled.
TRANSIENT_ERROR_MARKERS = (
    "Read timed out",
    "Max retries exceeded",
    "429",
    "502 Bad Gateway",
    "503",
    "upstream connect error",
    "no healthy upstream",
    "temporarily_unavailable",
    "Connection aborted",
    "Connection reset",
)

# System-wide error rate alerting
ERROR_RATE_THRESHOLD = 20  # errors across all users
ERROR_RATE_WINDOW = 300  # seconds
ALERT_COOLDOWN = 1800  # don't re-alert more than once per 30 min
