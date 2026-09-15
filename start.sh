#!/bin/bash

# Start Cobalt API in the background on port 9000
echo "Starting Cobalt API..."
cobalt-api &

# Wait for Cobalt to be ready
echo "Waiting for Cobalt to start..."
until curl -s http://localhost:9000/ > /dev/null; do
    sleep 2
done
echo "Cobalt is ready!"

# Start the Discord bot
echo "Starting Discord bot..."
python main.py
