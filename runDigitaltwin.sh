#!/bin/bash

# Run all three Python scripts simultaneously in the background
python3 test.pcap_replay_twin.py &    # Run the first script in the background
python3 test.5G.Net.test.py &         # Run the second script in the background
python3 resourcetest.py &             # Run the third script in the background

# Wait for all background jobs to finish
wait

