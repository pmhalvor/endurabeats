# This file is only used to help the user log in, 
# then store the credentials in a local file.

from flask import Flask, request
import os 

app = Flask(__name__)


@app.route('/')
def home():
    """
    Display the home page.
    """
    return 'You may close this tab.'


@app.route('/logged_in/<service>')
def logged_in(service):
    """
    Capture the redirected URL from Spotify or Strava's OAuth 2.0 flow.
    Store the code from the query string params as an environment variable.
    Example URL: http://localhost:3333/logged_in/spotify?grant_type=code&code=12344567&state=happy
    """
    code = request.args.get('code')
    os.environ[f'{service.upper()}_CODE'] = code
    return f'You may close this window. Code stored as environment variable {service.upper()}_CODE.'


@app.route('/get_code/<service>')
def get_code(service):
    """
    Capture the redirected URL from Spotify or Strava's OAuth 2.0 flow.
    Store the code from the query string params as an environment variable.
    Example URL: http://localhost:3333/logged_in/spotify?grant_type=code&code=12344567&state=happy
    """
    return os.environ.get(f'{service.upper()}_CODE', "None")


if __name__ == '__main__':
    app.run(debug=True, host='localhost', port=3333)
