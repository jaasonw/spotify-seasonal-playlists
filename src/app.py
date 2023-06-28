import sys
import threading
import traceback

import config
import constant
import database as db
import playlist
import spotipy
import logging
from DatabaseCacheHandler import DatabaseCacheHandler


def update_clients():
    """
    Refreshes the access tokens and updates the playlists for all clients in
    the cache
    """
    for user in db.get_users():
        if not user["active"]:
            continue
        logging.debug("Updating", user["user_id"])
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

            # reset the users error count if an update was successful
            db.update_user(user["user_id"], "error_count", 0)
        except Exception as e:
            log_error_to_database(user["user_id"], e)

            # if a user passes a certain error threshold, mark them as
            # inactive, they probably revoked our access
            if user["error_count"] > constant.ERROR_THRESHOLD:
                try:
                    db.update_user(user["user_id"], "active", "false")
                except Exception:
                    logging.error("Could not set user to inactive")


def log_error_to_database(user: str, e: Exception):
    message = "".join(traceback.format_tb(e.__traceback__))
    db.increment_field(user, "error_count")
    db.add_error(user, message)


def run(update_frequency: int):
    """
    Runs every n seconds on a separate thread
    update_frequency: how frequently to update in seconds
    """
    threading.Timer(
        update_frequency, run, kwargs=dict(update_frequency=update_frequency)
    ).start()
    try:
        update_clients()
    except Exception as e:
        log_error_to_database("SYSTEM", e)


if __name__ == "__main__":
    debug = False
    if len(sys.argv) >= 2:
        if sys.argv[1] == "--debug":
            debug = True
    # update faster if we're using the debug environment
    run(10 if debug else constant.UPDATE_FREQUENCY)

    # # debug server
    # if debug:
    #     from web_auth import auth_server

    #     # run the server in a background thread
    #     server_thread = threading.Thread(
    #         target=auth_server.run, kwargs=dict(port=config.port)
    #     )
    #     server_thread.run()
