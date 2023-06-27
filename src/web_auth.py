import requests
import spotipy
from flask import Flask, redirect, render_template, request
from spotipy.cache_handler import MemoryCacheHandler
from spotipy.oauth2 import SpotifyOAuth, SpotifyOauthError

import config
import constant
import database
from DatabaseCacheHandler import DatabaseCacheHandler
from playlist import update_playlist

auth_server = Flask(__name__)
auth_server.debug = False


@auth_server.route('/')
def frontpage():
    return render_template("index.html", url=config.redirect_uri)


@auth_server.route("/login")
def auth_page():
    # hacky way to store token in database
    # 1. use a MemoryCacheHandler to temporarily store token in ram
    # 2. use the api to retrieve the username
    # 3. transfer the token data from MemoryCacheHandler to DatabaseCacheHandler
    #    with username attached to the token
    tokenData = MemoryCacheHandler()
    oauth = SpotifyOAuth(
        scope=constant.SCOPE,
        cache_handler=tokenData,
        client_id=config.client_id,
        client_secret=config.client_secret,
        redirect_uri=config.redirect_uri + "/login",
    )
    # ask the user for authorization here
    if "code" not in request.args:
        return redirect(oauth.get_authorize_url())
    else:
        # TODO: backend logic probably doesn't belong here
        # we got the code here, use it to create a token
        print("Response Code: " + request.args["code"])
        try:
            # called for no reason other than to trigger a save_token_to_cache()
            # call inside the cache handler
            oauth.get_access_token(request.args["code"], as_dict=False)
        except SpotifyOauthError:
            return render_template("auth_fail.html", url=config.redirect_uri)

        # hacky database caching
        client = spotipy.Spotify(auth_manager=oauth)
        user = client.me()["id"]
        # create and store user in the Users table
        database.add_user(client.me()["id"])
        # transfer data from MemoryCacheHandler to DatabaseCacheHandler
        db = DatabaseCacheHandler(user)
        db.save_token_to_cache(tokenData.get_cached_token())

        # create new playlist for user
        user = database.get_user(user)
        update_playlist(client, user)

        return render_template("auth_success.html")
    return render_template("auth_success.html")


@auth_server.route("/logout")
def logout_page():
    return "work in progress, come back later!"
    # oauth = SpotifyOAuth(
    #     scope=constant.SCOPE,
    #     username="temp",
    #     cache_path=constant.CACHE_PATH + "/.cache-temp",
    #     client_id=config.client_id,
    #     client_secret=config.client_secret,
    #     redirect_uri=config.redirect_uri + "/logout"
    # )
    # # get another authorization code so we know who we're logging out
    # if ("code" not in request.args):
    #     return redirect(oauth.get_authorize_url())
    # else:
    #     logout_page = render_template("logout_sucess.html")
    #     print("Response Code: " + request.args["code"])
    #     try:
    #         token = oauth.get_access_token(request.args["code"], as_dict=False)
    #     except SpotifyOauthError:
    #         return render_template("logout_fail.html")
    #     # which we use to create a client
    #     client = spotipy.Spotify(auth=token)
    #     # this is apparently the pythonic way to do this
    #     try:
    #         os.remove(constant.CACHE_PATH + "/.cache-" + client.me()['id'])
    #     except OSError:
    #         logout_page = render_template(
    #             "logout_fail.html", id=client.me()['id'])
    #     try:
    #         os.remove(oauth.cache_path)
    #     except OSError:
    #         pass
    #     return logout_page


@auth_server.route("/check_status")
def status_check():
    return "work in progress, come back later!"
