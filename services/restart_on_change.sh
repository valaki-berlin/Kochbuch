#!/bin/bash

# Directory to watch
WATCH_DIR="/home/moebius/Geheimlabor/kochbuch"
# Service to restart
SERVICE_NAME="kochbuch"
WAIT_TIME=5  

# Monitor the directory but exclude the database and macOS noise
inotifywait -m -r --exclude "db/|static/recipe_images/|uploads|export//" -e modify -e create -e delete -e move --format '%w%f' "$WATCH_DIR" | while read FILE
do
    # Only log if NO timer is currently running (this is the first file)
    if [ ! -f /tmp/restart_timer.pid ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Triggered by: $FILE" 
    fi
    
    # Reset the timer if a new event occurs (standard debounce)
    if [ -f /tmp/restart_timer.pid ]; then
        kill $(cat /tmp/restart_timer.pid) 2>/dev/null
    fi

    (
        sleep $WAIT_TIME
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Settle time reached. Restarting $SERVICE_NAME." 
        sudo systemctl restart "$SERVICE_NAME"
        rm /tmp/restart_timer.pid
    ) & 
    
    echo $! > /tmp/restart_timer.pid
done

