from pyfiglet import Figlet
import subprocess
import time
from threading import Thread

def main():
    f = Figlet(font='slant')
    print(f.renderText('5G Network Test'))

def capture_traffic(container_name, duration=125):
    pcap_file_path = f"/open5gs/{container_name}_traffic_capture.pcap"
    try:
        # Start traffic capture
        print(f"Starting traffic capture on container {container_name}, interface ogstun")
        capture_command = f"docker exec -d {container_name} tcpdump -i ogstun -w {pcap_file_path}"
        subprocess.run(capture_command, shell=True, check=True)

        # Wait for the specified duration
        time.sleep(duration)

        # Stop traffic capture
        stop_command = f"docker exec {container_name} pkill tcpdump"
        subprocess.run(stop_command, shell=True, check=True)
        print(f"Traffic capture stopped for container '{container_name}'")

        # Download the capture file
        local_file_path = f"./{container_name}_traffic_capture.pcap"
        download_file(container_name, pcap_file_path, local_file_path)
        
    except subprocess.CalledProcessError as e:
        print(f"Error capturing traffic for container '{container_name}': {e}")

def download_file(container_name, container_file_path, local_file_path):
    try:
        download_command = f"docker cp {container_name}:{container_file_path} {local_file_path}"
        subprocess.run(download_command, shell=True, check=True)
        print(f"File {container_file_path} from container {container_name} downloaded to {local_file_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error downloading file from container '{container_name}': {e}")

def main_capture():
    containers = ['upf_sos', 'upf_ims', 'upf_internet', 'upf_default']

    # Start traffic capture on all containers simultaneously using threads
    threads = []
    for container in containers:
        thread = Thread(target=capture_traffic, args=(container,))
        thread.start()
        threads.append(thread)

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

if __name__ == "__main__":
    main()
    main_capture()

