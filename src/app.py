import sys
import time
import threading
import traceback as tb
from datetime import datetime as dt
from datetime import timezone as tz
from concurrent.futures import ThreadPoolExecutor

import config
import constant
import database as db
import playlist
import spotipy
import logging
from DatabaseCacheHandler import DatabaseCacheHandler


def update_single_user(user):
    """
    Updates the playlist for a single user
    """
    logging.debug(f"Updating {user['user_id']}")
    oauth = spotipy.oauth2.SpotifyOAuth(
        scope=constant.SCOPE,
        cache_handler=DatabaseCacheHandler(user["user_id"]),
        client_id=config.client_id,
        client_secret=config.client_secret,
        redirect_uri=config.redirect_uri,
    )
    try:
        client = spotipy.Spotify(auth_manager=oauth)
        playlist.update_playlist(client, user)

        # Mark as polled to prevent immediate retry
        timestamp = dt.now(tz=tz.utc).strftime("%Y-%m-%d %H:%M:%S")
        db.update_user(user["user_id"], "last_polled", timestamp)

        # reset the users error count if an update was successful
        if user.get("error_count", 0) > 0:
            db.update_user(user["user_id"], "error_count", 0)
    except Exception as e:
        log_error_to_database(user["user_id"], e)

        # if a user passes a certain error threshold, mark them as
        # inactive, they probably revoked our access
        if user.get("error_count", 0) > constant.ERROR_THRESHOLD:
            try:
                db.update_user(user["user_id"], "active", False)
            except Exception:
                logging.error("Could not set user to inactive")


def log_error_to_database(user: str, e: Exception):
    traceback = "".join(tb.format_tb(e.__traceback__))
    if user != "SYSTEM":
        db.increment_field(user, "error_count")
    db.add_error(user, error=str(e), traceback=traceback)


def run_worker_loop(update_frequency: int):
    """
    Continuously fetches stale users and updates them using a thread pool.
    """
    logging.info("Starting worker loop")
    
    with ThreadPoolExecutor(max_workers=constant.MAX_WORKERS) as executor:
        while True:
            try:
                # Update heartbeat - we are alive
                db.update_heartbeat("worker", "running", "Checking for users...")
                
                # Fetch batch of users needing update
                stale_users = db.get_users_needing_update(
                    update_frequency=update_frequency, 
                    limit=constant.BATCH_SIZE
                )
                
                if not stale_users:
                    # No work to do, sleep for a bit
                    db.update_heartbeat("worker", "idle", "No users needing update")
                    time.sleep(10)
                    continue
                
                logging.info(f"Found {len(stale_users)} users to update")
                db.update_heartbeat("worker", "processing", f"Updating {len(stale_users)} users")
                
                # Process batch concurrently
                futures = [executor.submit(update_single_user, user) for user in stale_users]
                
                # Wait for all tasks in the batch to complete
                for future in futures:
                    future.result()
                    
            except Exception as e:
                log_error_to_database("SYSTEM", e)
                db.update_heartbeat("worker", "error", str(e))
                # Sleep briefly to avoid hammering on error loop
                time.sleep(10)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    debug = False
    if len(sys.argv) >= 2:
        if sys.argv[1] == "--debug":
            debug = True
            
    # Run the worker loop
    run_worker_loop(10 if debug else constant.UPDATE_FREQUENCY)
