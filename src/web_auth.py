import os
import requests
import spotipy
from flask import Flask, redirect, render_template, request, session, flash
from functools import wraps
from spotipy.cache_handler import MemoryCacheHandler
from spotipy.oauth2 import SpotifyOAuth, SpotifyOauthError

import config
import constant
import database
from DatabaseCacheHandler import DatabaseCacheHandler
from playlist import update_playlist

auth_server = Flask(__name__)
auth_server.debug = False
auth_server.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')


@auth_server.context_processor
def inject_url_prefix():
    """Inject URL prefix into all templates"""
    return dict(url_prefix=config.url_prefix)


def login_required(f):
    """Decorator to require login for a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(config.url_prefix + '/login')
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to require admin privileges for a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(config.url_prefix + '/login')
        try:
            user = database.get_user(session['user_id'])
            if not user.get('is_admin', False):
                return "Access denied: Admin privileges required", 403
        except Exception as e:
            return f"Error checking admin status: {str(e)}", 500
        return f(*args, **kwargs)
    return decorated_function


@auth_server.route("/")
def frontpage():
    return render_template("index.html", url=config.redirect_uri)


@auth_server.route("/init")
def init_user():
    id = request.args.get("id")
    user = database.get_user(id)
    oauth = SpotifyOAuth(
        scope=constant.SCOPE,
        cache_handler=DatabaseCacheHandler(id),
        client_id=config.client_id,
        client_secret=config.client_secret,
        redirect_uri=config.redirect_uri + "/login",
    )
    client = spotipy.Spotify(auth_manager=oauth)
    update_playlist(client, user)
    return "OK", 200


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
        try:
            # called for no reason other than to trigger a save_token_to_cache()
            # call inside the cache handler
            oauth.get_access_token(request.args["code"], as_dict=False)
        except SpotifyOauthError:
            return render_template("auth_fail.html", url=config.redirect_uri)

        # hacky database caching
        client = spotipy.Spotify(auth_manager=oauth)
        user_id = client.me()["id"]
        # create user if they don't exist, or get existing user
        user = database.get_or_create_user(user_id)
        # transfer data from MemoryCacheHandler to DatabaseCacheHandler
        db = DatabaseCacheHandler(user_id)
        db.save_token_to_cache(tokenData.get_cached_token())

        # create new playlist for user
        update_playlist(client, user)

        # Store user_id in session
        session['user_id'] = user['user_id']

        return redirect(config.url_prefix + '/dashboard')
    return render_template("auth_success.html")


@auth_server.route("/logout")
def logout_page():
    """Clear session and log out user"""
    session.clear()
    return redirect(config.url_prefix + '/')


@auth_server.route("/dashboard")
@login_required
def dashboard():
    """User dashboard showing stats and account management"""
    try:
        user = database.get_user(session['user_id'])
        return render_template("dashboard.html", user=user, url=config.redirect_uri)
    except Exception as e:
        return f"Error loading dashboard: {str(e)}", 500


@auth_server.route("/unregister", methods=["POST"])
@login_required
def unregister():
    """Deactivate user account"""
    try:
        database.update_user(session['user_id'], "active", False)
        flash("Your account has been deactivated. You can reactivate by logging in again.", "success")
        session.clear()
        return redirect(config.url_prefix + '/')
    except Exception as e:
        flash(f"Error deactivating account: {str(e)}", "error")
        return redirect(config.url_prefix + '/dashboard')


@auth_server.route("/admin")
@admin_required
def admin_panel():
    """Admin panel to manage users"""
    try:
        users = database.get_users()
        # Sort by active (descending - active first), then by created date (descending - newest first)
        users.sort(key=lambda u: (-u.get('active', False), u.get('created', '')), reverse=False)
        return render_template("admin.html", users=users)
    except Exception as e:
        return f"Error loading admin panel: {str(e)}", 500


@auth_server.route("/admin/toggle-user", methods=["POST"])
@admin_required
def admin_toggle_user():
    """Toggle user active status"""
    user_id = request.form.get('user_id')
    if not user_id:
        flash("User ID required", "error")
        return redirect(config.url_prefix + '/admin')
    
    try:
        user = database.get_user(user_id)
        new_status = not user.get('active', True)
        database.update_user(user_id, "active", new_status)
        status_text = "activated" if new_status else "deactivated"
        flash(f"User {user_id} has been {status_text}", "success")
    except Exception as e:
        flash(f"Error toggling user: {str(e)}", "error")
    
    return redirect(config.url_prefix + '/admin')


@auth_server.route("/admin/errors")
@admin_required
def admin_errors():
    """View recent errors"""
    try:
        errors = database.get_recent_errors(limit=50)
        return render_template("admin_errors.html", errors=errors, url=config.redirect_uri)
    except Exception as e:
        return f"Error loading errors: {str(e)}", 500


@auth_server.route("/check_status")
def status_check():
    return "work in progress, come back later!"
