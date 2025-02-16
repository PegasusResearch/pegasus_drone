#!/usr/bin/env bash

# Start tmux session named 'ros' if not already running
tmux has-session -t ros 2>/dev/null
if [ $? != 0 ]; then
    tmux new-session -d -s ros
    tmux send-keys -t ros "source /home/pegasus/.bashrc && ros2 launch pegasus_drone pegasus.launch.py" C-m
fi