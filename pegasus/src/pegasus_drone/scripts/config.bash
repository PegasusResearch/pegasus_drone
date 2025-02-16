#!/usr/bin/env bash

# Create the service that automatically puts the jetson in the max power mode every time it boots
sudo cp services/jetson_clocks.service /etc/systemd/system/jetson_clocks.service
sudo systemctl daemon-reload
sudo systemctl enable jetson_clocks.service

# Create the service that automatically starts the pegasus code on boot
sudo cp services/pegasus.service /etc/systemd/system/pegasus.service
sudo systemctl daemon-reload
sudo systemctl enable pegasus.service
sudo systemctl start pegasus.service