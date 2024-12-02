import os
import subprocess
import time

# Configuration of interfaces
interfaces = {
    'tun0': 'upf_default',
    'tun1': 'upf_internet',
    'tun2': 'upf_ims',
    'tun3': 'upf_sos'
}

# Directories
traffic_dir = '/root/Desktop/traffic'
iteration_dir = os.path.join(traffic_dir, 'iteration')

# Ensure the directories exist
os.makedirs(traffic_dir, exist_ok=True)
os.makedirs(iteration_dir, exist_ok=True)

# Function to capture traffic on a single interface
def capture_traffic(interface, name, iteration, duration=120):
    # Define the file name pattern (e.g., upf_defaultone.pcap, upf_defaulttwo.pcap)
    pcap_filename = f"{name}{iteration}.pcap"
    pcap_filepath = os.path.join(traffic_dir, pcap_filename)

    # Start tcpdump
    print(f"Starting capture on {interface} to {pcap_filepath}")
    cmd = ['tcpdump', '-i', interface, '-w', pcap_filepath]
    process = subprocess.Popen(cmd)

    # Wait for the capture duration (2 minutes)
    time.sleep(duration)

    # Terminate tcpdump process after 2 minutes
    process.terminate()
    process.wait()

    # Move the captured pcap file to the iteration directory
    moved_pcap_filepath = os.path.join(iteration_dir, pcap_filename)
    print(f"Moving {pcap_filepath} to {moved_pcap_filepath}")
    os.rename(pcap_filepath, moved_pcap_filepath)

# Capture traffic from all interfaces simultaneously for 2 minutes, repeated for 10 iterations
def run_capture_for_all_interfaces():
    for iteration in range(1, 11):  # 10 iterations (2 minutes each)
        print(f"Starting iteration {iteration}")

        # Start capturing traffic on all interfaces at the same time
        processes = []
        for interface, name in interfaces.items():
            # Start each capture in a new process
            process = subprocess.Popen(['tcpdump', '-i', interface, '-w', f"{traffic_dir}/{name}{iteration}.pcap"])
            processes.append((process, interface, name))

        # Wait for 2 minutes (120 seconds)
        time.sleep(120)

        # Terminate all tcpdump processes after 2 minutes
        for process, interface, name in processes:
            process.terminate()
            process.wait()
            # Move pcap file to iteration directory
            pcap_filename = f"{name}{iteration}.pcap"
            pcap_filepath = os.path.join(traffic_dir, pcap_filename)
            moved_pcap_filepath = os.path.join(iteration_dir, pcap_filename)
            print(f"Moving {pcap_filepath} to {moved_pcap_filepath}")
            os.rename(pcap_filepath, moved_pcap_filepath)

        print(f"Iteration {iteration} completed.\n")

# Run the entire capturing process
if __name__ == "__main__":
    run_capture_for_all_interfaces()
