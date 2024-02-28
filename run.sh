#!/bin/bash
# exports 
source credentials.sh

# activate env
source $CONDA_PATH
conda activate endurabeats


if [[ -n $SPOTIFY_CLIENT_ID ]]; then
    echo "Spotify credentials set"
else
    echo "Spotify credentials not set"
    #exit 1
fi

if [[ -n $STRAVA_CLIENT_ID ]]; then
    echo "Strava credentials set"
else
    echo "Strava credentials not set"
    #exit 1
fi


# Start Flask login app in the background
echo "Starting login client..."
python src/login.py &

# Save the process ID of the Flask app
FLASK_PID=$!

# Wait for Flask app to start up (you may need to adjust the sleep duration)
sleep 3

# Run authorize.py
echo "Running authorization workflow..."
python src/authorize.py > logs/auth.log

# Kill the Flask server
echo "Killing login client..."
kill $FLASK_PID

# Run tracklists.py
echo "Updating tracklists..."
python src/tracklists.py > logs/tracklists.log

echo "Exiting endurabeats..."
