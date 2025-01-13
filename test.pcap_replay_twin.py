import pexpect
import sys
import os
import stat
import time
import datetime
import logging
import subprocess
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(filename='file_transfer.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Remote and local details
remote_dir = "/root/Desktop/traffic/iteration/"
remote_host = "10.196.31.1"
username = "root"
password = os.getenv("SCP_PASSWORD", "5gbasestation+!")
file_patterns = ["upf_default", "upf_internet", "upf_sos", "upf_ims"]  # Base file names

# Determine the current working directory
local_dir = os.getcwd()

# Function to build numbered file names based on iteration count
def build_file_names(counter):
    return {f"{file_pattern}{counter}.pcap": f"{file_pattern}:/open5gs/{file_pattern}{counter}.pcap" for file_pattern in file_patterns}

# Function to build tcpreplay commands dynamically
def build_tcpreplay_commands(counter):
    return {f"{file_pattern}{counter}.pcap": f"tcpreplay -i ogstun /open5gs/{file_pattern}{counter}.pcap" for file_pattern in file_patterns}

# Function to transfer a single file
def transfer_file(remote_file, local_file, filename):
    # Define the local directory and ensure the target folder exists
    current_dir = os.getcwd()
    target_dir = os.path.join(current_dir, 'physicaltwin.traffic')
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    
    # Define the local file path
    local_file = os.path.join(target_dir, filename)
    
    # Construct SCP command to transfer file from remote to local
    scp_command = f"scp {username}@{remote_host}:{remote_file} {local_file}"

    try:
        # Use pexpect to spawn the SCP command and interact with the process
        child = pexpect.spawn(scp_command, encoding='utf-8')
        i = child.expect(['Are you sure you want to continue connecting', 'password:', pexpect.EOF, pexpect.TIMEOUT])

        # Handle the expected prompts and responses from SCP
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

        # Optionally, copy the file to Docker containers if applicable
        docker_copy_file(local_file)

    except pexpect.exceptions.EOF:
        logging.error("SCP process exited unexpectedly.")
    except pexpect.exceptions.TIMEOUT:
        logging.error("Timeout occurred while waiting for SCP response.")
    except Exception as e:
        logging.error(f"Error occurred: {str(e)}")

# Function to copy the transferred file into Docker containers for processing
def docker_copy_file(local_file):
    container_target = containers.get(os.path.basename(local_file))
    if container_target:
        container, target_path = container_target.split(':')
        docker_command = f"docker cp {local_file} {container}:{target_path}"
        try:
            result = subprocess.run(docker_command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logging.info(f"File {local_file} copied to Docker container {container} at {target_path}.")
            # Analyze the file inside the container using tcpreplay
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

# Function to delete local .pcap files
def delete_local_files(counter):
    try:
        for file_pattern in file_patterns:
            file_path = os.path.join(local_dir, f"{file_pattern}{counter}.pcap")
            if os.path.exists(file_path):
                os.remove(file_path)
                logging.info(f"Local file {file_path} removed.")
            else:
                logging.info(f"Local file {file_path} does not exist, no need to delete.")
    except Exception as e:
        logging.error(f"Error removing local file: {str(e)}")

# Function to delete .pcap files from Docker containers
def delete_docker_files(counter):
    try:
        for file_pattern in file_patterns:
            file_name = f"{file_pattern}{counter}.pcap"
            container_target = containers.get(file_name)
            if container_target:
                container, target_path = container_target.split(':')
                docker_rm_command = f"docker exec {container} rm {target_path}"
                try:
                    result = subprocess.run(docker_rm_command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    logging.info(f"File {target_path} removed from Docker container {container}.")
                except subprocess.CalledProcessError as e:
                    logging.error(f"Error removing file from Docker container: {e.stderr.decode()}")
    except Exception as e:
        logging.error(f"Error removing Docker file: {str(e)}")

# Function to transfer files concurrently using ThreadPoolExecutor
def transfer_files_concurrently(counter):
    with ThreadPoolExecutor() as executor:
        futures = []
        current_files = build_file_names(counter)
        for file, container_path in current_files.items():
            remote_file_path = f"{remote_dir}{file}"
            local_file_path = os.path.join(local_dir, file)
            futures.append(executor.submit(transfer_file, remote_file_path, local_file_path, file))  # Pass 'file' as the filename
        for future in futures:
            future.result()

# Main function to handle file transfers periodically
def transfer_files_periodically():
    try:
        counter = 1  # Start the cycle at 1 for the numbered files
        next_cycle = datetime.datetime.now()  # Schedule the first cycle for immediate start

        while True:
            now = datetime.datetime.now()
            if now >= next_cycle:
                logging.info(f"Starting cycle {counter}")

                # Cleanup old files before transferring new ones
                delete_local_files(counter)
                delete_docker_files(counter)

                # Set up containers and tcpreplay commands for the current iteration
                global containers, tcpreplay_commands
                containers = build_file_names(counter)
                tcpreplay_commands = build_tcpreplay_commands(counter)

                # Transfer the new files and process them
                transfer_files_concurrently(counter)
                logging.info(f"Cycle {counter} completed successfully.")

                # Increment the cycle counter and schedule the next cycle (2 minutes later)
                counter += 1
                next_cycle = now + datetime.timedelta(minutes=2)

            # Short sleep to prevent CPU overuse
            time.sleep(1)

    except KeyboardInterrupt:
        logging.info("File transfer interrupted by user.")
        sys.exit(0)

# Main entry point
if __name__ == "__main__":
    transfer_files_periodically()

