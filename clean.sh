#!/bin/bash

# Clear Mininet setup
sudo mn -c

# Stop all running Docker containers
docker stop $(docker ps -aq)

# Remove all Docker containers
docker container prune -f

# If the first argument is "log", clear log files
if [ "$1" == "log" ]; then
    cd log && sudo rm -f *.log 
fi

# Delete specific network interfaces
sudo ip link delete s1-ue
sudo ip link delete s2-s3
sudo ip link delete s2-s1
sudo ip link delete gnb-s1
sudo ip link delete s1-gnb
sudo ip link delete s1-cp
sudo ip link delete gnb-s2
sudo ip link delete s2-gnb
sudo ip link delete s3-cp
sudo ip link delete s1-ue1
sudo ip link delete s1-ue2
sudo ip link delete s1-ue3
sudo ip link delete s2-upf_mec
sudo ip link delete s3-upf
sudo ip link delete s1-uegnb
sudo ip link delete s4-upf_mec
sudo ip link delete upf_mec-s4

# Additional interfaces for servers and UPFs
sudo ip link delete s4-mec_server
sudo ip link delete s4-voip_server
sudo ip link delete s4-video_server
sudo ip link delete s4-file_server
sudo ip link delete s4-upf_internet
sudo ip link delete s4-upf_industry

# Clear screen
clear

echo "Cleanup complete."

