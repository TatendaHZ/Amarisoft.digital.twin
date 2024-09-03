import pexpect
import sys
import os
import stat
import time
import logging
import subprocess
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(filename='file_transfer.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Remote and local details
remote_dir = "/root/Desktop/traffic/"
remote_host = "10.196.31.247"
username = "root"
password = os.getenv("SCP_PASSWORD", "5gbasestation+!")
files = ["upf_default.pcap", "upf_internet.pcap", "upf_ims.pcap", "upf_sos.pcap"]
containers = {
    "upf_default.pcap": "upf_default:/open5gs/upf_default.pcap",
    "upf_internet.pcap": "upf_internet:/open5gs/upf_internet.pcap",
    "upf_sos.pcap": "upf_sos:/open5gs/upf_sos.pcap",
    "upf_ims.pcap": "upf_ims:/open5gs/upf_ims.pcap"
}
tcpreplay_commands = {
    "upf_sos.pcap": "tcpreplay -i ogstun /open5gs/upf_sos.pcap",
    "upf_ims.pcap": "tcpreplay -i ogstun /open5gs/upf_ims.pcap",
    "upf_default.pcap": "tcpreplay -i ogstun /open5gs/upf_default.pcap",
    "upf_internet.pcap": "tcpreplay -i ogstun /open5gs/upf_internet.pcap",
}

# Determine the current working directory
local_dir = os.getcwd()

# Function to transfer a single file
def transfer_file(remote_file, local_file):
    scp_command = f"scp {username}@{remote_host}:{remote_file} {local_file}"

    try:
        child = pexpect.spawn(scp_command, encoding='utf-8')
        i = child.expect(['Are you sure you want to continue connecting', 'password:', pexpect.EOF, pexpect.TIMEOUT])

        if i == 0:
            child.sendline('yes')
            child.expect('password:')
            child.sendline(password)
        elif i == 1:
            child.sendline(password)
        elif i == 2:
            logging.error("Connection closed unexpectedly.")
            sys.exit(1)
        elif i == 3:
            logging.error("Timeout occurred.")
            sys.exit(1)

        child.expect(pexpect.EOF)
        logging.info(f"File transferred successfully to {local_file}!")
        os.chmod(local_file, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        
        # Copy the file to Docker containers if applicable
        docker_copy_file(local_file)

    except pexpect.exceptions.EOF:
        logging.error("SCP process exited unexpectedly.")
    except pexpect.exceptions.TIMEOUT:
        logging.error("Timeout occurred while waiting for SCP response.")
    except Exception as e:
        logging.error(f"Error occurred: {str(e)}")

# Function to copy file into Docker containers
def docker_copy_file(local_file):
    container_target = containers.get(os.path.basename(local_file))
    if container_target:
        container, target_path = container_target.split(':')
        docker_command = f"docker cp {local_file} {container}:{target_path}"
        try:
            result = subprocess.run(docker_command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logging.info(f"File {local_file} copied to Docker container {container} at {target_path}.")
            # Analyze the file inside the container
            analyze_in_container(container, target_path)
        except subprocess.CalledProcessError as e:
            logging.error(f"Error copying file to Docker container: {e.stderr.decode()}")

# Function to analyze .pcap files inside Docker containers using tcpreplay
def analyze_in_container(container, file_path):
    analyze_command = tcpreplay_commands.get(os.path.basename(file_path))
    if analyze_command:
        docker_exec_command = f"docker exec {container} {analyze_command}"
        try:
            result = subprocess.run(docker_exec_command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logging.info(f"tcpreplay output for {file_path} in container {container}:\n{result.stdout.decode()}")
        except subprocess.CalledProcessError as e:
            logging.error(f"Error during tcpreplay execution: {e.stderr.decode()}")

# Function to handle file transfers concurrently
def transfer_files_concurrently():
    with ThreadPoolExecutor() as executor:
        futures = []
        for file in files:
            remote_file_path = f"{remote_dir}{file}"
            local_file_path = os.path.join(local_dir, file)
            futures.append(executor.submit(transfer_file, remote_file_path, local_file_path))
        for future in futures:
            future.result()

# Main function to handle file transfers periodically
def transfer_files_periodically():
    try:
        while True:
            transfer_files_concurrently()
            logging.info("All files transferred and analyzed successfully. Waiting for the next cycle...")
            time.sleep(120)  # Wait for 2 minutes before the next transfer cycle

    except KeyboardInterrupt:
        logging.info("File transfer interrupted by user.")
        sys.exit(0)

if __name__ == "__main__":
    transfer_files_periodically()

