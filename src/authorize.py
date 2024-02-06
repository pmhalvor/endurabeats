import base64
import json
import os 
import requests
import six
import time 
import webbrowser


SPOTIFY_CLIENT_ID = os.environ['SPOTIFY_CLIENT_ID']
SPOTIFY_CLIENT_SECRET = os.environ['SPOTIFY_CLIENT_SECRET']
STRAVA_CLIENT_ID = os.environ['STRAVA_CLIENT_ID']
STRAVA_CLIENT_SECRET = os.environ['STRAVA_CLIENT_SECRET']

REDIRECT_URI = "http://localhost:3333"
RETRY_COUNT = 5
WAIT_TIME = 5  # also increases by 5 seconds each retry


# Helper functions 
def make_headers(client_id, client_secret) -> dict:
    # base64 encoded string
    client = base64.b64encode(
        six.text_type(f'{client_id}:{client_secret}').encode('ascii')
    )
    return {"Authorization": f"Basic {client.decode('ascii')}", "Content-Type": "application/x-www-form-urlencoded"}


def get_code(service):
    # give page time to load
    time.sleep(3)

    for i in range(RETRY_COUNT):
        code = requests.get(f"{REDIRECT_URI}/get_code/{service}").text
        if code == "None":
            print(f"Attempt {i+1} for {service} failed.")
            for j in range(WAIT_TIME*(i+1), 0, -1):
                print(f"\rRetrying in {j} seconds...", end=" ", flush=True)
                time.sleep(1)
        else:
            break 
    return code


def save_tokens(tokens, filename):
    with open(filename, 'w') as f:
        json.dump(tokens, f)


# Main functions
def get_spotify_tokens_from_code(code) -> dict:
    if code == "None":
        raise Exception("No code provided")
    
    # parameters for post request
    OAUTH_TOKEN_URL = "https://accounts.spotify.com/api/token"
    PAYLOAD = {
        'grant_type': 'authorization_code',
        'redirect_uri': REDIRECT_URI + '/logged_in/spotify',
        'code': code,
    }
    HEADERS = make_headers(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET)
    
    # post request
    response = requests.post(
        url=OAUTH_TOKEN_URL,
        data=PAYLOAD,
        headers=HEADERS
    )
    tokens = response.json()
    tokens["expires_at"] = round(time.time()) + 3600  # 1 hour from now

    return tokens


def get_strava_tokens_from_code(code) -> dict:
    if code == "None":
        raise Exception("No code provided")

    params = {
        "client_id": STRAVA_CLIENT_ID,
        "client_secret": STRAVA_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code"
    }

    response = requests.post("https://www.strava.com/oauth/token", params=params)
    return response.json()


def authorize_spotify(scopes=['user-read-currently-playing', 'user-read-recently-played']) -> dict:
    # parameters for post request
    OAUTH_TOKEN_URL = "https://accounts.spotify.com/authorize"
    PAYLOAD = {
        'client_id': SPOTIFY_CLIENT_ID,
        'scope': ",".join(scopes),
        'redirect_uri': REDIRECT_URI + '/logged_in/spotify',
        'state': "spotify",
        'response_type': 'code'
    }
    url = f"{OAUTH_TOKEN_URL}?" + "&".join([f"{k}={v}" for k, v in PAYLOAD.items()])
    webbrowser.open(url)

    code = get_code('spotify')
    tokens = get_spotify_tokens_from_code(code)
    save_tokens(tokens, os.environ.get("SPOTIFY_TOKENS_PATH", "spotify_tokens.json"))

    return tokens


def authorize_strava(scopes=['activity:read_all', 'activity:write']) -> dict:
    params = {
        "client_id": STRAVA_CLIENT_ID,
        "client_secret": STRAVA_CLIENT_SECRET,
        "response_type": "code",
        "approval_prompt": "auto",
        "scope": ",".join(scopes),
        "redirect_uri": REDIRECT_URI + '/logged_in/strava',
        "state": "strava"
    }

    url = (
        "https://www.strava.com/oauth/authorize?" +
        "&".join([f"{k}={v}" for k, v in params.items()])
    )

    webbrowser.open(url)

    code = get_code('strava')
    tokens = get_strava_tokens_from_code(code)
    save_tokens(tokens, os.environ.get("STRAVA_TOKENS_PATH", "strava_tokens.json"))

    return tokens


def refresh_spotify_tokens(refresh_token) -> dict:
    print("Spotifyccess token expired, refreshing")

    # parameters for post request
    OAUTH_TOKEN_URL = "https://accounts.spotify.com/api/token"
    PAYLOAD = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
    }
    HEADERS = make_headers(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET)
    
    # post request
    response = requests.post(
        url=OAUTH_TOKEN_URL,
        data=PAYLOAD,
        headers=HEADERS
    )

    if response.status_code != 200:
        raise Exception(f"Refresh failed: {response.text}")

    tokens = response.json()
    tokens["expires_at"] = round(time.time()) + 3600  # 1 hour from now
    save_tokens(tokens, os.environ.get("SPOTIFY_TOKENS_PATH", "spotify_tokens.json"))

    return tokens


def refresh_strava_tokens(refresh_token) -> dict:
    print("Strava access token expired, refreshing")

    params = {
        "client_id": STRAVA_CLIENT_ID,
        "client_secret": STRAVA_CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }

    response = requests.post("https://www.strava.com/oauth/token", params=params)

    if response.status_code != 200:
        raise Exception(f"Refresh failed: {response.text}")

    tokens = response.json()
    save_tokens(tokens, os.environ.get("STRAVA_TOKENS_PATH", "strava_tokens.json"))

    return tokens


def get_tokens(service) -> dict:
    def _authorize_service():
        if service == "spotify":
            return authorize_spotify()
        elif service == "strava":
            return authorize_strava()
        else:
            raise Exception("Service not recognized")
    
    service = service.lower()

    if os.path.exists(os.environ.get(f"{service.upper()}_TOKENS_PATH", f"{service}_tokens.json")):
        
        with open(os.environ.get(f"{service.upper()}_TOKENS_PATH", f"{service}_tokens.json"), 'r') as f:
            tokens = json.load(f)

            if tokens.get("access_token") is None or tokens.get("refresh_token") is None:
                tokens = _authorize_service()

    else:
        _authorize_service() 

    with open(os.environ.get(f"{service}_TOKENS_PATH", f"{service}_tokens.json"), 'r') as f:
        tokens = json.load(f)

    # check if token is expired
    if time.time() > tokens["expires_at"]:  # purposely fails if tokens["expires_at"] is not set
        tokens = (
            refresh_spotify_tokens(tokens["refresh_token"])
            if service == "spotify" else 
            refresh_strava_tokens(tokens["refresh_token"])
        )

    return tokens


if __name__ == '__main__':
    ""
    # Expected authorization flow
    # 1. User stores client id and secret in .env file 
    # 2. User runs app.py (or main.py or whatever) to start the Flask server
    # 3. The spotify url with client id, secret, and scopes is opened in the browser
    # 4. User logs in and authorizes the app
    # 5. The redirect url contains the code is stored as an env var in the Flask server
    # 6. The the main app then uses the code to get the access and refresh tokens
    # 7. The tokens are stored in spotify_tokens.json
    # 8. Steps 3-7 are repeated for Strava

    spotify_tokens = get_tokens("spotify")
    strava_tokens = get_tokens("strava")