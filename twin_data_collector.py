import paramiko
import os
import re
import ipaddress
import json

# Define the remote host and credentials
remote_host = "10.xx.xx.xx"
username = "xxxxx"
password = os.getenv("SCP_PASSWORD", "xxxxxxx")
remote_path = "/root/mme/config/mme.cfg"  # Path to the configuration file on the remote host
local_output_filename = "slice_info_with_qci_and_ip.json"  # Local output file

# Users information (added)
users = ["user1", "user2"]
bandwidth = "100MHz"  # Bandwidth for each slice

# Function to convert an IP address (in string format) to an integer
def ip_to_int(ip_str):
    return int(ipaddress.IPv4Address(ip_str))

# Function to convert an integer back to an IP address string
def int_to_ip(ip_int):
    return str(ipaddress.IPv4Address(ip_int))

# Function to extract slice names, qci values, and the modified IP addresses
def extract_slice_info(config_data):
    # Regular expressions to find access_point_name, first_ip_addr, and qci
    slice_pattern = r'access_point_name:\s*"([^"]+)"'
    ip_pattern = r'first_ip_addr:\s*"([^"]+)"'
    qci_pattern = r'qci:\s*(\d+)'

    slice_info = []

    # Extract all access point names (slice names)
    access_point_names = re.findall(slice_pattern, config_data)

    # For each access point, extract its corresponding qci values and first_ip_addr
    for access_point_name in access_point_names:
        # Find the section related to each access point, containing qci and first_ip_addr
        slice_section = re.search(rf'access_point_name:\s*"{access_point_name}"(.*?erabs.*?)(?=\n\s*access_point_name|$)', config_data, re.DOTALL)

        if slice_section:
            # Extract the first_ip_addr
            ip_match = re.search(rf'first_ip_addr:\s*"([^"]+)"', slice_section.group(0))
            if ip_match:
                first_ip_addr = ip_match.group(1)
                # Convert the IP address to an integer and subtract 1
                ip_int = ip_to_int(first_ip_addr) - 1
                modified_ip = int_to_ip(ip_int)
            else:
                modified_ip = "N/A"  # In case the IP address is missing

            # Extract the qci values for the current access point
            qci_values = re.findall(qci_pattern, slice_section.group(0))

            # For each qci value found, append it to the slice_info list along with modified IP
            for qci in qci_values:
                slice_info.append({
                    'slice_name': access_point_name,
                    'qci': qci,
                    'ip_address': modified_ip,
                    'users': users,  # List of users
                    'bandwidth': bandwidth  # Bandwidth for each slice
                })

    return slice_info

# Function to write extracted information to a file locally (in JSON format)
def write_to_file(slice_info, output_filename):
    with open(output_filename, 'w') as file:
        json.dump(slice_info, file, indent=4)  # Save as pretty-printed JSON
    print(f"Information has been written to {output_filename}")

# SSH and SFTP operations
def fetch_and_process_remote_file():
    try:
        # Create an SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # Connect to the remote host
        ssh.connect(remote_host, username=username, password=password)
        print(f"Connected to {remote_host}")

        # Use SFTP to fetch the remote file
        sftp = ssh.open_sftp()
        remote_file = sftp.open(remote_path, 'r')
        config_data = remote_file.read().decode('utf-8')
        remote_file.close()

        # Process the configuration file
        slice_info = extract_slice_info(config_data)

        if slice_info:
            # Write the extracted information to a local file (in JSON format)
            write_to_file(slice_info, local_output_filename)
        else:
            print("No slice information or QCI values found.")

        # Optionally, you can also transfer the output file back to the remote server if needed
        # sftp.put(local_output_filename, '/remote/path/to/save/output_file.json')

        # Close the SFTP session and SSH connection
        sftp.close()
        ssh.close()

    except Exception as e:
        print(f"Error: {e}")

# Main function to initiate the process
if __name__ == '__main__':
    fetch_and_process_remote_file()

