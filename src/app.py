from spotipy.exceptions import SpotifyException
from DatabaseCacheHandler import DatabaseCacheHandler
import config
import constant
import database as db
import playlist
import spotipy
import sys
import threading
import traceback
from datetime import datetime as dt, time
from datetime import timezone as tz


def update_clients():
    """
    Refreshes the access tokens and updates the playlists for all clients in
    the cache
    """
    for user in db.get_users():
        if db.get_field(user, "active") != "false":
            print("updating", user)
            oauth = spotipy.oauth2.SpotifyOAuth(
                scope=constant.SCOPE,
                cache_handler=DatabaseCacheHandler(user),
                client_id=config.client_id,
                client_secret=config.client_secret,
                redirect_uri=config.redirect_uri
            )
            try:
                client = spotipy.Spotify(auth_manager=oauth)
                playlist.update_playlist(client)

                # reset the users error count if an update was successful
                db.update_user(user, "error_count", 0)
            except SpotifyException as e:
                # we hit a rate limit wait 30 seconds and retry
                if e.code == 429:
                    time.sleep(30)
                    try:
                        playlist.update_playlist(client)
                    except Exception as e:
                        log_error_to_database(user, e)
            except Exception as e:
                log_error_to_database(user, e)

                # if a user passes a certain error threshold, mark them as
                # inactive, they probably revoked our access
                if db.get_field(user, "error_count") > constant.ERROR_THRESHOLD:
                    try:
                        db.update_user(user, "active", "false")
                    except Exception:
                        print("Could not set user to inactive")


def log_error_to_database(user: str, e: Exception):
    timestamp = dt.now(tz=tz.utc).strftime('%Y-%m-%d %H:%M:%S')
    message = str(e)
    message = timestamp + ": " + message
    db.increment_field(user, "error_count")
    db.add_error(user, message)


def run(update_frequency: int):
    """
    Runs every n seconds on a separate thread
    update_frequency: how frequently to update in seconds
    """
    threading.Timer(update_frequency, run, kwargs=dict(
        update_frequency=update_frequency)).start()
    try:
        update_clients()
    except Exception as e:
        print(e)
        with open(constant.SRC_PATH + '/../error.log', 'a') as f:
            f.write(str(e))
            f.write(traceback.format_exc())


if __name__ == "__main__":
    debug = False
    if len(sys.argv) >= 2:
        if sys.argv[1] == "--debug":
            debug = True
    # update faster if we're using the debug environment
    run(10 if debug else constant.UPDATE_FREQUENCY)

    # debug server
    if debug:
        from web_auth import auth_server
        # run the server in a background thread
        server_thread = threading.Thread(
            target=auth_server.run,
            kwargs=dict(port=config.port)
        )
        server_thread.run()
