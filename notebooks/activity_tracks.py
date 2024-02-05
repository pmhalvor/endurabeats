# %% [markdown]
# # Activity Tracks
# 
# Find the tracks played during an activity.

# %% [markdown]
# # Load

# %%
import json
import os 
import requests as r 
import pandas as pd


# %%

def load_tokens(filename):
    with open(filename, 'r') as f:
        return json.load(f)

spotify_tokens = load_tokens(os.environ["SPOTIFY_TOKENS_PATH"])
strava_tokens = load_tokens(os.environ["STRAVA_TOKENS_PATH"])

# strava_tokens, spotify_tokens

# %% [markdown]
# # Load data from APIs

# %%
def get_recent_played(access_token):
    URL = "https://api.spotify.com/v1/me/player/recently-played"    # api-endpoint for recently played
    HEAD = {'Authorization': 'Bearer '+ access_token}               # provide auth. credentials
    PARAMS = {'limit':50}	                                        # default here is 20
    content = r.get(url=URL, headers=HEAD, params=PARAMS)
    return content.json()


def get_activities(access_token):
    URL = "https://www.strava.com/api/v3/athlete/activities"    # api-endpoint for recently played
    HEAD = {"Authorization": f"Bearer {access_token}"}
    content = r.get(URL, headers=HEAD)
    return content.json()


raw_recent_played = get_recent_played(spotify_tokens["access_token"])
raw_activities = get_activities(strava_tokens["access_token"])

# %%
raw_activities

# %%
raw_recent_played

# %% [markdown]
# # Extra data
# Some extra data saved to help overlap with some activities. 

# %%
extra_tracks = pd.read_csv("../spotify/history_240130_240203.csv")
extra_tracks

# %% [markdown]
# # Convert to dataframe 

# %%
recent_played_df = pd.DataFrame(raw_recent_played["items"])

recent_played_df.head()

# %%
activities_df = pd.DataFrame(raw_activities)

print(*activities_df.columns.to_list(), sep="\n")

# %% [markdown]
# # Preprocessing 
# Prepare the dataframes to be easily comparable. 

# %%
def preprocess_activities(activities_df):
    activities_df = activities_df.copy()

    # stored in Oslo timezone
    activities_df["start"] = pd.to_datetime(activities_df["start_date"])

    # build end_date from start_date and elapsed_time
    activities_df["end"] = activities_df["start"] + pd.to_timedelta(activities_df["elapsed_time"], unit="s")

    # start and end are in UTC, convert to Oslo timezone
    activities_df["start"] = activities_df["start"].dt.tz_convert("Europe/Oslo")
    activities_df["end"] = activities_df["end"].dt.tz_convert("Europe/Oslo")

    # drop unnecessary columns
    return activities_df[["athlete", "id", "start", "end"]]


activities = preprocess_activities(activities_df)
activities.head()

# %%
def preprocess_tracks(recent_played_df):
    recent_played_df = recent_played_df.copy().sort_values("played_at", ascending=False)

    # convert to datetime
    recent_played_df["start"] = pd.to_datetime(recent_played_df["played_at"], format='mixed')

    # build end_time
    expected_end_time = recent_played_df["start"] + pd.to_timedelta(recent_played_df["track"].apply(lambda x: x["duration_ms"]), unit="ms")
    next_song_start = recent_played_df["start"].shift(1)
    recent_played_df["end"] = expected_end_time.combine(next_song_start, min)

    # rename to start, end, name, artist, track id
    recent_played_df["track_name"] = recent_played_df["track"].apply(lambda x: x["name"])
    recent_played_df["artist"] = recent_played_df["track"].apply(lambda x: x["artists"][0]["name"])
    recent_played_df["id"] = recent_played_df["track"].apply(lambda x: x["id"])

    # start and end are in UTC, convert to Oslo timezone
    recent_played_df["start"] = recent_played_df["start"].dt.tz_convert("Europe/Oslo")
    recent_played_df["end"] = recent_played_df["end"].dt.tz_convert("Europe/Oslo")

    # drop unnecessary columns
    return recent_played_df[["start", "end", "track_name", "artist", "id"]]

tracks = preprocess_tracks(recent_played_df)
tracks.head()

# %%
def preprocess_extra_tracks(extra_tracks):
    extra_tracks = extra_tracks.copy().sort_values("start", ascending=False)
    extra_tracks["start"] = pd.to_datetime(extra_tracks["start"])

    # build end_time
    expected_end_time = pd.to_datetime(extra_tracks["start"]) + pd.to_timedelta(30, unit="m")
    next_song_start = pd.to_datetime(extra_tracks["start"]).shift(1)
    extra_tracks["end"] = expected_end_time.combine(next_song_start, min)

    # rename name to track_name to help pandas
    if "name" in extra_tracks.columns:
        extra_tracks["track_name"] = extra_tracks["name"]

    # my timezone is off, need to add an hour (hack)
    if extra_tracks.start.iloc[0].hour < 6:
        extra_tracks["start"] = extra_tracks["start"] + pd.to_timedelta(1, unit="h")
        extra_tracks["end"] = extra_tracks["end"] + pd.to_timedelta(1, unit="h")

    # start and end are in UTC, convert to Oslo timezone
    extra_tracks["start"] = extra_tracks["start"].dt.tz_convert("Europe/Oslo")
    extra_tracks["end"] = extra_tracks["end"].dt.tz_convert("Europe/Oslo")

    return extra_tracks[["start", "end", "track_name", "artist", "id"]]

extra_tracks = preprocess_extra_tracks(extra_tracks).sort_values("start", ascending=True)
extra_tracks.head()

# %%
# merge all tracks, drop duplicates and sort by start time
all_tracks = pd.concat([tracks, extra_tracks]).drop_duplicates().sort_values("start").reset_index(drop=True)
all_tracks.head()

# %% [markdown]
# # Find songs per activity

# %%
activities.head()

# %%
recent_activities = activities[activities["start"] > all_tracks["start"].min()].copy()

recent_activities

# %%
x = recent_activities.iloc[-1]

def overlap(x, y):
    return (x.start < y.end) & (x.end > y.start)

def build_track_str(x):
    return f"{x.track_name} - {x.artist}"

def get_tracklist(x, y):
    return y[overlap(x, y)].apply(build_track_str, axis=1).to_list()

get_tracklist(x, all_tracks)

# %%
recent_activities["tracklist"] = recent_activities.apply(lambda x: get_tracklist(x, all_tracks), axis=1)
recent_activities


# %% [markdown]
# Sweet! Now our activities have the list of tracks played during them. NExt step is to update the descriptions of the activities with these tracks.  

# %% [markdown]
# # Add tracklists to activity descriptions
# To do this properly, we first need to [`get_activity(id)`](https://developers.strava.com/docs/reference/#api-Activities-getActivityById) to make sure the description doesn't already have a tracklist.
# If there is no tracklist present, we can then [`update_activity(id, params={})`](https://developers.strava.com/docs/reference/#api-Activities-updateActivityById) with description + tracklist.

# %%
def get_activity(id, access_token=strava_tokens["access_token"]):
    URL = f"https://www.strava.com/api/v3/activities/{id}"    # api-endpoint for recently played
    HEAD = {"Authorization": f"Bearer {access_token}"}
    content = r.get(URL, headers=HEAD)
    return content.json()


def update_activity(id, data, access_token=strava_tokens["access_token"]):
    URL = f"https://www.strava.com/api/v3/activities/{id}"    # api-endpoint for recently played
    HEAD = {"Authorization": f"Bearer {access_token}"}
    content = r.put(URL, headers=HEAD, data=data)
    return content


def contains_tracklist(description):
    return (description is not None) and "Tracklist" in description


def add_tracklist(id, tracklist, access_token=strava_tokens["access_token"]):
    activity = get_activity(id, access_token)
    description = activity["description"]
    tracks = "\n".join(tracklist)
    if contains_tracklist(description) or len(tracks) == 0:
        return description
    description = (
        description + tracklist_template.format(tracks) 
        if description else tracklist_template.format(tracks)
    )
    content = update_activity(id, {"description": description}, access_token)
    print(content.json()) if content.status_code != 200 else None
    return get_activity(id, access_token)["description"]


tracklist_template = """
Tracklist:
{}

Uploaded automatically using https://github.com/pmhalvor/endurabeats/
"""

add_tracklist(10672137037, [])

# %%
activity_tracks = recent_activities.copy().apply(lambda x: add_tracklist(x.id, x.tracklist), axis=1)
activity_tracks

# %%



