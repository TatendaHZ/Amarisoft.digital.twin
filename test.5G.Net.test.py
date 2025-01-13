from pyfiglet import Figlet
import subprocess
import time
from threading import Thread
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    f = Figlet(font='slant')
    print(f.renderText('5G Network Test'))

def capture_traffic(container_name, iteration, duration=120, cleanup=False):
    pcap_file_path = f"/open5gs/{container_name}d{iteration}.pcap"  # File name with iteration
    try:
        # Start traffic capture
        logging.info(f"Starting traffic capture on container {container_name}, interface ogstun, iteration {iteration}")
        capture_command = f"docker exec -d {container_name} tcpdump -i ogstun -w {pcap_file_path}"
        subprocess.run(capture_command, shell=True, check=True)

        # Check if tcpdump is running
        check_command = f"docker exec {container_name} pgrep tcpdump"
        if subprocess.run(check_command, shell=True).returncode == 0:
            logging.info(f"TCPDump is running on container {container_name}.")
        else:
            logging.error(f"TCPDump failed to start on container {container_name}.")
            return  # Exit if tcpdump did not start

        logging.info(f"Waiting for {duration} seconds for traffic capture on container {container_name}...")
        time.sleep(duration)

        # Stop traffic capture
        stop_command = f"docker exec {container_name} pkill tcpdump"
        subprocess.run(stop_command, shell=True, check=True)
        logging.info(f"Traffic capture stopped for container '{container_name}' on iteration {iteration}")

        # Download the capture file
        local_file_path = f"./digitaltwin.traffic/{container_name}d{iteration}.pcap"  # Download with the same iteration name
        download_file(container_name, pcap_file_path, local_file_path)

        # Optionally remove the capture file from the container after downloading
        if cleanup:
            cleanup_command = f"docker exec {container_name} rm {pcap_file_path}"
            subprocess.run(cleanup_command, shell=True, check=True)
            logging.info(f"Removed pcap file {pcap_file_path} from container {container_name}")

    except subprocess.CalledProcessError as e:
        logging.error(f"Error capturing traffic for container '{container_name}' on iteration {iteration}: {e}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")

def download_file(container_name, container_file_path, local_file_path):
    try:
        download_command = f"docker cp {container_name}:{container_file_path} {local_file_path}"
        subprocess.run(download_command, shell=True, check=True)
        logging.info(f"File {container_file_path} from container {container_name} downloaded to {local_file_path}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error downloading file from container '{container_name}': {e}")

def main_capture():
    containers = ['upf_sos', 'upf_ims', 'upf_internet', 'upf_default']
    iterations = 10  # Number of iterations
    duration = 120  # Duration of each capture

    for i in range(1, iterations + 1):  # Loop for 10 iterations
        threads = []
        for container in containers:
            thread = Thread(target=capture_traffic, args=(container, i, duration))
            thread.start()
            threads.append(thread)

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Add a pause between iterations
        if i < iterations:
            logging.info(f"Waiting {duration} seconds before starting iteration {i + 1}...")
            time.sleep(1)  # Short delay between iterations (you can increase this if needed)

if __name__ == "__main__":
    main()
    main_capture()

