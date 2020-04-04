import config
import constant
import spotipy
import os
from spotipy.oauth2 import SpotifyOAuth
from flask import Flask, redirect, request
from client_manager import ClientManager

auth_server = Flask(__name__)
auth_server.debug = False

@auth_server.route('/')
def main():
    oauth = SpotifyOAuth(
        scope = constant.SCOPE, 
        username = "temp",
        cache_path = constant.CACHE_PATH + "/.cache-temp",
        client_id = config.client_id,
        client_secret = config.client_secret,
        redirect_uri = config.redirect_uri
    )
    # ask the user for authorization here
    if ("code" not in request.args):
        return redirect(oauth.get_authorize_url())
    else:
        # we got the code here, use it to create a token
        print("Response Code: " + request.args["code"])
        token = oauth.get_access_token(request.args["code"], as_dict=False)
        # which we use to create a client
        client = spotipy.Spotify(auth=token)
        os.rename(constant.CACHE_PATH + "/.cache-temp",
                  constant.CACHE_PATH + "/.cache-" + client.me()['id'])
        ClientManager.clients.append(client)
        print("Authenticated: " + ClientManager.clients[-1].me()['id'])
        return "Successfully authenticated, you may close this now"