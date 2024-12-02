#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import subprocess
from comnetsemu.cli import CLI, spawnXtermDocker
from comnetsemu.net import Containernet, VNFManager
from mininet.link import TCLink
from mininet.log import info, setLogLevel
from mininet.node import Controller, RemoteController
from python_modules.Open5GS import Open5GS
import json, time, yaml

def wait_for_uesimtun(ue, user_id, n_slices):
    info(f"\n*** Waiting for the network to be ready for user {user_id}... it can take some seconds\n")
    time.sleep(20)
    output = ue.cmd('ifconfig')
    while f"uesimtun{n_slices - 1}" not in output:
        info("\n*** Still waiting...\n")
        time.sleep(5)
        output = ue.cmd('ifconfig')

if __name__ == "__main__":

    AUTOTEST_MODE = os.environ.get("COMNETSEMU_AUTOTEST_MODE", 0)

    setLogLevel("info")

    prj_folder = "/home/vagrant/comnetsemu/Amari"
    mongodb_folder = "/home/vagrant/mongodbdata"

    env = dict()

    net = Containernet(controller=Controller, link=TCLink)
    mgr = VNFManager(net)
    script_dir = os.path.abspath(os.path.join('./', os.path.dirname(sys.argv[0])))
    shared_dir = os.path.join(script_dir, 'shared')
    
    # Initialize slices, users, and subnet data
    slices = {}  # This will store the slices by their numeric index
    n_slices = 0  # Counter for slice number
    users_slices = {}  # This will store slices per user, indexed by user numeric ID
    users_n_slices = {}  # This will store the number of slices per user

    # Read the slice information from the JSON file
    with open('slice_info_with_qci_and_ip.json', 'r') as file:
        answers = json.load(file)

    # Create a set to track unique slices (based on DNN, IP, Subnet)
    unique_slices = {}

    # Global variable for generating IP
    global_ip = 112
    seen_dnn = {}
    subnet_ip_assignment = {}

    # Assign a numeric user ID starting from 1
    user_id_map = {}  # Mapping of user names to numeric user ids
    user_id_counter = 1

    # Iterate over the slice data to process users and their slices
    for slice_info in answers:
        slice_name = slice_info['slice_name']
        ip_address = slice_info['ip_address']
        users = slice_info['users']
        bandwidth = slice_info['bandwidth']  # Remove unit for bandwidth (e.g., MHz)

        # Process each user in the users list
        for user_name in users:
            # Map user names to numeric user ids if not already mapped
            if user_name not in user_id_map:
                user_id_map[user_name] = user_id_counter
                user_id_counter += 1

            user_id = user_id_map[user_name]

            # If this is the first time we encounter this user, initialize their slice information
            if user_id not in users_slices:
                users_slices[user_id] = {}

            # If this is the first time we encounter this user, initialize their slice count
            if user_id not in users_n_slices:
                users_n_slices[user_id] = 0

            # Check if the slice has already been added to unique_slices
            if slice_name not in seen_dnn:
                # Assign IP and subnet from the JSON file
                ip = '192.168.0.' + str(global_ip)  # IP is generated based on global_ip
                subnet = ip_address  # Subnet is directly taken from the slice_info in JSON file
                
                # Add slice to unique_slices if it's not there already
                unique_slices[slice_name] = {
                    'dnn': slice_name,
                    'bw': int(bandwidth.replace('MHz', '').strip()),  # Remove unit
                    'ip': ip,
                    'subnet': subnet
                }

                # Add the slice to the slices dictionary with a number key
                slices[n_slices] = unique_slices[slice_name]

                # Increment the global slice count and global_ip by 1 for each unique slice
                n_slices += 1
                global_ip += 1  # Increment IP by 1 for the next slice

                # Mark this slice as seen
                seen_dnn[slice_name] = True

            # Add the slice for the user in the numbered format (sequential slice numbers for each user)
            users_slices[user_id][users_n_slices[user_id]] = unique_slices[slice_name]
            
            # Increment the slice count for this user (the number of slices this user has)
            users_n_slices[user_id] += 1

    # Ensure that users_n_slices contains the total number of slices for each user
    # Here, we print the result
    print("Users n_slices (Number of slices per user):")
    print(n_slices)
    with open('./open5gs/config/smf.yaml', 'r') as read_file:
        contents = yaml.safe_load(read_file)
        contents['smf']['subnet'].clear()
        contents['smf']['subnet'].extend([None] * int(n_slices))
        contents['upf']['pfcp'].clear()
        contents['upf']['pfcp'].extend([None] * int(n_slices))
        for i in range(int(n_slices)):
            contents['smf']['subnet'][i] = {
                'addr': slices[i]['subnet'] + '/24',
                'dnn': slices[i]['dnn']
            }
            contents['upf']['pfcp'][i] = {
                'addr': slices[i]['ip'],
                'dnn': slices[i]['dnn']
            }
    with open('./open5gs/config/smf.yaml', 'w') as dump_file:
        yaml.dump(contents, dump_file)

    with open('./open5gs/config/nssf.yaml', 'r') as read_file:
        contents = yaml.safe_load(read_file)
        contents['nssf']['nsi'].clear()
        contents['nssf']['nsi'].extend([None] * int(n_slices))
        for i in range(int(n_slices)):
            contents['nssf']['nsi'][i] = {
                'addr': '127.0.0.10',
                'port': 7777,
                's_nssai': {'sst': i + 1, 'sd': 1}
            }
    with open('./open5gs/config/nssf.yaml', 'w') as dump_file:
        yaml.dump(contents, dump_file)

    with open('./open5gs/config/amf.yaml', 'r') as read_file:
        contents = yaml.safe_load(read_file)
        contents['amf']['guami'][0]['plmn_id'] = {'mcc': '001', 'mnc': '01'}
        contents['amf']['tai'][0]['plmn_id'] = {'mcc': '001', 'mnc': '01'}
        contents['amf']['plmn_support'][0]['plmn_id'] = {'mcc': '001', 'mnc': '01'}
        contents['amf']['plmn_support'][0]['s_nssai'].clear()
        contents['amf']['plmn_support'][0]['s_nssai'].extend([None] * int(n_slices))
        for i in range(int(n_slices)):
            contents['amf']['plmn_support'][0]['s_nssai'][i] = {'sst': i + 1, 'sd': 1}
    with open('./open5gs/config/amf.yaml', 'w') as dump_file:
        yaml.dump(contents, dump_file)
        
    directory = "ueransim/config"
    for user_id, user_slices in users_slices.items():
        filename = f"open5gs-ue{user_id}.yaml"
        
        filepath = os.path.join(directory, filename)
        with open('./ueransim/config/open5gs-ue.yaml', 'r') as read_file:
            contents = yaml.safe_load(read_file)
    
        contents['supi'] = f"imsi-00101123456789{user_id}"
        contents['sessions'] = []
        contents['configured-nssai'] = []
    
        for i in range(users_n_slices[user_id]):
            contents['sessions'].append({
                'type': 'IPv4',
                'slice': {'sst': i + 1, 'sd': 1},
                'emergency': False
            })
        
            contents['configured-nssai'].append({
                'sst': i + 1,
                'sd': 1
            })
    
        with open(filepath, 'w') as dump_file:
            yaml.dump(contents, dump_file)

        print(f"Created {filename} for user {user_id}")
      
    with open('./ueransim/config/open5gs-gnb.yaml', 'r') as read_file:
        contents = yaml.safe_load(read_file)
        contents['slices'].clear()
        contents['slices'].extend([None] * int(n_slices))
        for i in range(int(n_slices)):
            contents['slices'][i] = {'sst': i + 1, 'sd': 1}
    with open('./ueransim/config/open5gs-gnb.yaml', 'w') as dump_file:
        yaml.dump(contents, dump_file)

    # create yaml config files for each upf
    for i in range(int(n_slices)):
        with open('./open5gs/config/default_yaml/upf.yaml', 'r') as read_file:
            contents = yaml.safe_load(read_file)
            contents['logger'] = {'file': '/open5gs/install/var/log/open5gs/upf_' + slices[i]['dnn'] + '.log'}
            contents['upf'] = {
                'pfcp': [{'addr': slices[i]['ip']}],
                'gtpu': [{'addr': slices[i]['ip']}],
                'subnet': [
                    {'addr': slices[i]['subnet'] + '/24',
                     'dnn': slices[i]['dnn'],
                     'dev': 'ogstun'}
                ]
            }
        with open('./open5gs/config/upf_' + slices[i]['dnn'] + '.yaml', 'w') as dump_file:
            yaml.dump(contents, dump_file)

    
    info("*** Add controllers\n")    
    c0 = net.addController("c0", controller=Controller, port=6634)
    
    info("*** Adding switch\n")
    s1 = net.addSwitch("s1")
    s2 = net.addSwitch("s2")
    s3 = net.addSwitch("s3")
   
    
    info("*** Adding links\n")
    net.addLink(s1, s2, bw=1000, delay="10ms", intfName1="s1-s2", intfName2="s2-s1")
    net.addLink(s2, s3, bw=1000, delay="50ms", intfName1="s2-s3", intfName2="s3-s2")

    info("*** Adding Host for open5gs CP\n")
    cp = net.addDockerHost(
        "cp",
        dimage="my5gc_v2-4-4",
        ip="192.168.0.111/24",
        dcmd="bash /open5gs/install/etc/open5gs/5gc_cp_init.sh",
       
        docker_args={
            "ports": {"3000/tcp": 3000},
            "volumes": {
                prj_folder + "/log": {
                    "bind": "/open5gs/install/var/log/open5gs",
                    "mode": "rw",
                },
                mongodb_folder: {
                    "bind": "/var/lib/mongodb",
                    "mode": "rw",
                },
                prj_folder + "/open5gs/config": {
                    "bind": "/open5gs/install/etc/open5gs",
                    "mode": "rw",
                },
                "/etc/timezone": {
                    "bind": "/etc/timezone",
                    "mode": "ro",
                },
                "/etc/localtime": {
                    "bind": "/etc/localtime",
                    "mode": "ro",
                },
            },
        },
    )

    for i in range(int(n_slices)):
        info("*** Adding Host for open5gs UPF " + slices[i]['dnn'] + "\n")
        env["COMPONENT_NAME"] = "upf_" + slices[i]['dnn']
        env["SUBNET"] = slices[i]['subnet']
        host_name = "upf_" + slices[i]['dnn'] 
        host = net.addDockerHost(
            "upf_" + slices[i]['dnn'],
            dimage="my5gc_v2-4-4",
            ip=slices[i]['ip'] + "/24",
            dcmd="bash /open5gs/install/etc/open5gs/temp/5gc_up_init.sh",
            docker_args={
                "environment": env,
                "volumes": {
                    prj_folder + "/log": {
                        "bind": "/open5gs/install/var/log/open5gs",
                        "mode": "rw",
                    },
                    prj_folder + "/open5gs/config": {
                        "bind": "/open5gs/install/etc/open5gs/temp",
                        "mode": "rw",
                    },
                    "/etc/timezone": {
                        "bind": "/etc/timezone",
                        "mode": "ro",
                    },
                    "/etc/localtime": {
                        "bind": "/etc/localtime",
                        "mode": "ro",
                    },
                },
                "cap_add": ["NET_ADMIN"],
                "sysctls": {"net.ipv4.ip_forward": 1},
                "devices": "/dev/net/tun:/dev/net/tun:rwm"
            },
        )
        net.addLink(host, s2, bw=1000, delay="1ms", intfName1="upf_" + slices[i]['dnn'] + "-s2",
                    intfName2="s2-upf_" + slices[i]['dnn'])
       

    info("*** Adding gNB\n")
    env["COMPONENT_NAME"] = "gnb"
    gnb = net.addDockerHost(
        "gnb",
        dimage="myueransim_v3-2-6",
        ip="192.168.0.131/24",
        dcmd="bash /mnt/ueransim/open5gs_gnb_init.sh",
        docker_args={
            "environment": env,
            "volumes": {
                prj_folder + "/ueransim/config": {
                    "bind": "/mnt/ueransim",
                    "mode": "rw",
                },
                prj_folder + "/log": {
                    "bind": "/mnt/log",
                    "mode": "rw",
                },
                "/etc/timezone": {
                    "bind": "/etc/timezone",
                    "mode": "ro",
                },
                "/etc/localtime": {
                    "bind": "/etc/localtime",
                    "mode": "ro",
                },
                "/dev": {"bind": "/dev", "mode": "rw"},
            },
            "cap_add": ["NET_ADMIN"],
            "devices": "/dev/net/tun:/dev/net/tun:rwm"
        },
    )

    for user_id, user_slices in users_slices.items():
        # Define the environment variables for each UE dynamically
        env = {
            "XDG_RUNTIME_DIR": "/tmp/runtime-dir",
            "SDL_VIDEODRIVER": "dummy",
            "SDL_RENDER_DRIVER": "software",
            "SDL_AUDIODRIVER": "dsp",
            "COMPONENT_NAME": f"ue{user_id}"  
        }
    
        # Setup the IP address for the UE based on user_id
        ue_ip = f"192.168.0.{132 + user_id}/24"           
        dcmd = f"bash /mnt/ueransim/open5gs_ue{user_id}_init.sh"    
        # Logging the addition of a new UE
        info("*** Adding UE\n")               
        ue = net.addDockerHost(
            f"ue{user_id}",
            dimage="myueransim_v3-2-6",
            ip=ue_ip,
            dcmd=dcmd,
            docker_args={
                "environment": env, 
                "volumes": {
                    prj_folder + "/ueransim/config": {
                        "bind": "/mnt/ueransim",
                        "mode": "rw",
                    },
                    prj_folder + "/log": {
                        "bind": "/mnt/log",
                        "mode": "rw",
                    },
                        "/etc/timezone": {
                        "bind": "/etc/timezone",
                        "mode": "ro",
                    },
                    "/etc/localtime": {
                        "bind": "/etc/localtime",
                        "mode": "ro",
                    },
                    "/dev": {"bind": "/dev", "mode": "rw"},
                },
                "cap_add": ["NET_ADMIN"],
                "devices": "/dev/net/tun:/dev/net/tun:rwm"
            },
        )

        # Establishing a network link with predefined parameters
        net.addLink(ue, s1, bw=1000, delay="1ms", intfName1=f"ue{user_id}-s1", intfName2=f"s1-ue{user_id}")
    net.addLink(cp, s3, bw=1000, delay="1ms", intfName1="cp-s1", intfName2="s1-cp")
    net.addLink(gnb, s1, bw=1000, delay="1ms", intfName1="gnb-s1", intfName2="s1-gnb")
    
    o5gs = Open5GS("172.17.0.2", "27017")
    o5gs.removeAllSubscribers()
    
    print(f"*** Open5GS: Init subscriber for UE 0")
    folder_path = 'python_modules'



    # Load slice information from the JSON file
    with open('slice_info_with_qci_and_ip.json', 'r') as f:
        slice_info = json.load(f)

    # Create a dictionary for quick lookup of qci by slice name
    slice_qci_dict = {}
    for slice_data in slice_info:
        slice_qci_dict[slice_data['slice_name']] = slice_data['qci']

    # Load the default data for the subscriber profile template
    with open(os.path.join(folder_path, 'subscriber_profile.json'), 'r') as file:
        default_data = json.load(file)

    # Generate profiles for each user
    for user_id, user_slices in users_slices.items():
        user_data = default_data.copy()
        user_imsi = f"00101123456789{user_id}"
        user_data['imsi'] = user_imsi
        user_data['slice'] = []

        # Iterate over each slice of the user
        for i in range(users_n_slices[user_id]):
            slice_name = user_slices[i]['dnn']  # Extract slice name (e.g., 'ims', 'sos', etc.)
        
            # Get the QCI from slice_qci_dict based on the slice name
            qci = slice_qci_dict.get(slice_name, '9')  # Default to '9' if slice name not found
        
            # Set the default_indicator for the first slice or based on your logic
            if i != 0:
                default = None
            else:
                default = True
        
            # Append the slice data to the user's profile
            user_data['slice'].append({
                'sst': i + 1,
                'default_indicator': default,
                'sd': '000001',
                'session': [{
                    'name': slice_name,
                    'type': 3,
                    'pcc_rule': [],
                    'ambr': {
                        'Comment': 'unit=2 ==> Mbps',
                        'uplink': {'value': int(user_slices[i]['bw']), 'unit': 2},
                        'downlink': {'value': int(user_slices[i]['bw']), 'unit': 2}
                    },
                    'qos': {
                        'index': int(qci),  # Use the qci value retrieved from slice_qci_dict
                        'arp': {
                            'priority_level': 15,
                            'pre_emption_capability': 1,
                            'pre_emption_vulnerability': 1
                        }
                    }
                }]
            })

        # Write the user's profile to a JSON file
        json_filename = f'subscriber_profile{user_id}.json'
        with open(os.path.join(folder_path, json_filename), 'w') as file:
            json.dump(user_data, file)

        print(f"Created {json_filename} for user {user_id}")

         
    folder_path = 'python_modules'
    for user_id, user_slices in users_slices.items():
        json_filename = f'subscriber_profile{user_id}.json'
        with open(os.path.join(folder_path, json_filename), 'r') as f:
            profile = json.load(f)

        o5gs = Open5GS("172.17.0.2", "27017")
        o5gs.addSubscriber(profile)
      
        print(f"Added subscriber profile from {json_filename} for user {user_id} to Open5GS")
        
        
    info("\n*** Starting network\n")
    net.start()
 
    if not AUTOTEST_MODE:
        for user_id, user_slices in users_slices.items():
            ue_container_name = f"ue{user_id}"
            ue = net.get(ue_container_name)
            wait_for_uesimtun(ue, user_id, users_n_slices[user_id])
        ue2 = net.get("ue2")        
        ue2.cmd('ifconfig uesimtun0 192.168.2.6 netmask 255.255.255.0')  
        ue2.cmd('ifconfig uesimtun1 192.168.4.6 netmask 255.255.255.0')  
           
        
                    

        CLI(net)
    net.stop()     
     
