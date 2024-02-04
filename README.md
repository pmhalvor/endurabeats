# endurabeats
A light-weight API integration that syncs music played over Spotify to activity posted on Strava.



## Getting Started
In order to use this software, you will need to have Spotify Premium and a Strava account. You will also need to register an application with both Spotify and Strava to obtain the necessary API keys.
Both APIs have good documentation in place to help you get started.
- [Strava API](https://developers.strava.com/docs/getting-started/)
- [Spotify API](https://developer.spotify.com/documentation/web-api/)

### Installation
To install this software, you will need to clone this repository and install the necessary dependencies. You can do this by running the following commands in your terminal:
```
git clone git@github.com:pmhalvor/endurabeats.git
cd endurabeats
```

Then, install the necessary dependencies:
```
pip install -r requirements.txt
```

## Configuration
If you followed the steps on the Strava and Spotify "Getting Started" pages, you should now have a client id and secret for each service. To use these in this app, you will need to store these credentials as local environment variables using `export MY_VAR=value`.

You should also add the paths in which you want the app to store the tokens for each service. Using cached tokens will allow you to avoid having to authenticate endurabeats each time the app is run, relying only on access and refresh tokens. If these paths are somewhere in the current repo, they should be added to your `.gitignore` file to prevent your tokens from being uploaded to a GitHub. By default, we add all files ending with `tokens.json` to the `.gitignore` file.

Your export command should look something like this:
```bash
export SPOTIFY_CLIENT_ID=your_spotify_client_id
export SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
export SPOTIFY_TOKENS_PATH=/path/to/project/endurabeats/spotify_tokens.json

export STRAVA_CLIENT_ID=your_strava_client_id
export STRAVA_CLIENT_SECRET=your_strava_client_secret
export STRAVA_TOKENS_PATH=/path/to/project/endurabeats/strava_tokens.json
```

You can add these commands to your `.bashrc` or `.zshrc` file to have them run every time you open a new terminal window.
I'll store mine in a file called `credentials.sh` and add it to `.gitignore``. 

```bash
source credentials.sh
```

## Running the app
With your credentials in place, you can now run the `run.sh` script.
```bash
bash run.sh
```

If this is your first time running the script, a browser window will open and prompt you to log in to both Spotify and Strava. Note, that the code and tokens generated during this workflow will only be stored on your local machine, meaning if you want to run this code somewhere else, you need to copy these credentials there or go through the authorization process again. 

If you were properly able to log in and authenticate, you should see your terminal print the stages of the workflow being executed. The process ends by printing out the activity id of the activities that got updated descriptions, along with the beginning of the Tracklist string. 

Finally, the code ends with the following messages:
```
Complete.
Exiting endurabeats...
```
If you only see the final message, that means everything was ok, except you don't have any recent activity on Strava with overlapping activity on Spotify. Spotify only allows a user to access their last 50 songs. Looking further back into history would require storing the song history in a database, which is not implemented in this version of the app.


## Future Work
- Modularize the code to call from single command line operation
- Add tests
- (If allowed) Add database to store song history
- Add more details about each track (url, audio features, etc.)
- Build tracklist into a linkable playlist on Spotify


## Acknowledgments

We would like to acknowledge the following API providers, making this project possible:

- [Strava Developers](https://developers.strava.com/)
- [Spotify for Developers](https://developer.spotify.com/)

If you use or distribute this software, please ensure proper attribution to this repository and these providers.
