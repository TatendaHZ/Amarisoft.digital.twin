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
    
    slices = {}
    n_slices = 0
    users_slices = {}
    users_n_slices = {}

    # Read answers from the file
    with open('user_slices_answers.txt', 'r') as file:
        answers = file.readlines()
    # Extract number of users
    n_users = int(answers.pop(0).strip())

    global_ip = 112
    global_subnet = 2
    seen_dnn = {}
    subnet_ip_assignment = {}

    for user_id in range(1, n_users + 1):
        user_slices = {}
        user_n_slices = int(answers.pop(0).strip())

        for i in range(user_n_slices):
            dnn = answers.pop(0).strip()
            bw = answers.pop(0).strip()
        
            if dnn in subnet_ip_assignment:
                ip = subnet_ip_assignment[dnn]['ip']
                subnet = subnet_ip_assignment[dnn]['subnet']
            else:
                ip = '192.168.0.' + str(global_ip)
                subnet = '192.168.' + str(global_subnet) +'.1'
                subnet_ip_assignment[dnn] = {'ip': ip, 'subnet': subnet}
                global_ip += 1
                global_subnet += 1
        
            user_slices[i] = {
                'dnn': dnn,
                'bw': bw,
                'ip': ip,
                'subnet': subnet
            }

            if dnn not in seen_dnn:
                seen_dnn[dnn] = True
                slices[n_slices] = user_slices[i]
                n_slices += 1

        users_slices[user_id] = user_slices
        users_n_slices[user_id] = len(user_slices)  # Update to count only unique slices for this user
    
        # Print information for each user
        print(f"User {user_id} has {len(user_slices)} slices:")
        for slice_info in user_slices.values():
            print(f"  DNN: {slice_info['dnn']}, BW: {slice_info['bw']}, IP: {slice_info['ip']}, Subnet: {slice_info['subnet']}")

    # Print total number of unique slices across all users
    print(f"Total number of unique slices: {n_slices}")


  
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

    with open(os.path.join(folder_path, 'subscriber_profile.json'), 'r') as file:
        default_data = json.load(file)

    for user_id, user_slices in users_slices.items():
        user_data = default_data.copy()
        user_imsi = f"00101123456789{user_id}"
        user_data['imsi'] = user_imsi
        user_data['slice'] = []
        for i in range(users_n_slices[user_id]):
            if i != 0:
                default = None
            else:
                default = True
        
            dnn = user_slices[i]['dnn']
        
            # Determine the QoS index based on the DNN
            if dnn == 'ims':
                qos_index = 5
            elif dnn == 'sos':
                qos_index = 5
            else:
                qos_index = 9
        
            user_data['slice'].append({
                'sst': i + 1,
                'default_indicator': default,
                'sd': '000001',
                'session': [{
                    'name': dnn,
                    'type': 3,
                    'pcc_rule': [],
                    'ambr': {
                        'Comment': 'unit=2 ==> Mbps',
                        'uplink': {'value': int(user_slices[i]['bw']), 'unit': 2},
                        'downlink': {'value': int(user_slices[i]['bw']), 'unit': 2}
                    },
                    'qos': {
                        'index': qos_index,
                        'arp': {
                            'priority_level': 15,
                            'pre_emption_capability': 1,
                            'pre_emption_vulnerability': 1
                        }
                    }
                }]
            })
   
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

