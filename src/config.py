import os

client_id = os.environ["client_id"]
client_secret = os.environ["client_secret"]
redirect_uri = os.environ["redirect_uri"]
port = os.environ["port"]
pocketbase_url = os.environ["pocketbase_url"]
pocketbase_username = os.environ["pocketbase_username"]
pocketbase_password = os.environ["pocketbase_password"]
frontend_url = os.environ.get("frontend_url")
flask_secret_key = os.environ.get(
    "FLASK_SECRET_KEY", "dev-secret-key-change-in-production"
)
url_prefix = os.environ.get("URL_PREFIX", "")
