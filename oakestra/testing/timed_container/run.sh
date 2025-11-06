#!/bin/sh

# Default to 20 seconds if no argument is provided
TIME=${1:-20}

echo "Container will run for $TIME seconds..."
sleep "$TIME"
echo "Exiting container now."