import json
import os 
import requests as r 
import pandas as pd


TRACKLIST_TEMPLATE = """
Tracklist:
{}

Uploaded automatically using https://github.com/pmhalvor/endurabeats/
"""


def load_tokens(filename):
    with open(filename, 'r') as f:
        return json.load(f)


# API calls
def get_recent_played(access_token):
    URL = "https://api.spotify.com/v1/me/player/recently-played"    # api-endpoint for recently played
    HEAD = {'Authorization': 'Bearer '+ access_token}               # provide auth. credentials
    PARAMS = {'limit':50}	                                        # default here is 20
    content = r.get(url=URL, headers=HEAD, params=PARAMS)
    return content.json()


def get_activities(access_token):
    URL = "https://www.strava.com/api/v3/activities"    # api-endpoint for activities
    HEAD = {"Authorization": f"Bearer {access_token}"}
    content = r.get(URL, headers=HEAD)
    return content.json()


# Data processing
def preprocess_activities(raw_activities):
    activities_df = pd.DataFrame(raw_activities)

    # stored in Oslo timezone
    activities_df["start"] = pd.to_datetime(activities_df["start_date"])

    # build end_date from start_date and elapsed_time
    activities_df["end"] = activities_df["start"] + pd.to_timedelta(activities_df["elapsed_time"], unit="s")

    # start and end are in UTC, convert to Oslo timezone
    activities_df["start"] = activities_df["start"].dt.tz_convert("Europe/Oslo")
    activities_df["end"] = activities_df["end"].dt.tz_convert("Europe/Oslo")

    # drop unnecessary columns
    return activities_df[["athlete", "id", "start", "end"]]


def preprocess_tracks(raw_recent_played):
    recent_played_df = pd.DataFrame(raw_recent_played["items"]).sort_values("played_at")

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


def overlap(x, y):
    return (x.start < y.end) & (x.end > y.start)


def build_track_str(x):
    return f"{x.track_name} - {x.artist}"


def get_tracklist(x, y):
    return y[overlap(x, y)].apply(build_track_str, axis=1).to_list()


# Update activity with tracklist
def get_activity(id, access_token):
    URL = f"https://www.strava.com/api/v3/activities/{id}"    # api-endpoint for recently played
    HEAD = {"Authorization": f"Bearer {access_token}"}
    content = r.get(URL, headers=HEAD)
    return content.json()


def update_activity(id, data, access_token):
    URL = f"https://www.strava.com/api/v3/activities/{id}"    # api-endpoint for recently played
    HEAD = {"Authorization": f"Bearer {access_token}"}
    content = r.put(URL, headers=HEAD, data=data)
    return content


def contains_tracklist(description):
    return (description is not None) and "Tracklist" in description


def add_tracklist(id, tracklist, access_token):
    activity = get_activity(id, access_token)
    description = activity["description"]
    tracks = "\n".join(tracklist)
    if contains_tracklist(description) or len(tracks) == 0:
        return description
    description = (
        description + TRACKLIST_TEMPLATE.format(tracks) 
        if description else TRACKLIST_TEMPLATE.format(tracks)
    )
    content = update_activity(id, {"description": description}, access_token)
    print(content.json()) if content.status_code != 200 else None
    return get_activity(id, access_token)["description"]



if __name__ == '__main__':
    # Load tokens
    spotify_tokens = load_tokens(os.environ["SPOTIFY_TOKENS_PATH"])
    strava_tokens = load_tokens(os.environ["STRAVA_TOKENS_PATH"])

    # Get recent data from APIs
    raw_recent_played = get_recent_played(spotify_tokens["access_token"])
    raw_activities = get_activities(strava_tokens["access_token"])

    # Preprocess data
    tracks = preprocess_tracks(raw_recent_played)
    activities = preprocess_activities(raw_activities)

    # Filter most recent activities
    recent_activities = activities[activities["start"] > tracks["start"].min()].copy()

    # Get tracklist for each activity
    recent_activities["tracklist"] = recent_activities.apply(get_tracklist, y=tracks, axis=1)

    # Add tracklist to each activity
    update_description = lambda x: add_tracklist(x.id, x.tracklist, strava_tokens["access_token"])
    recent_activities["descriptions"] = recent_activities.apply(update_description, axis=1)

    # Print updated descriptions
    print(recent_activities[["id", "descriptions"]])
    print("Complete.")