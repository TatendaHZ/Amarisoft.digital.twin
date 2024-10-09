#!/bin/bash

if [[ -z "$COMPONENT_NAME" ]]; then
	echo "Error: COMPONENT_NAME environment variable not set"; exit 1;
fi

ip tuntap add name ogstun mode tun
ip addr add $SUBNET/24 dev ogstun
ip link set ogstun up
iptables -t nat -A POSTROUTING -s $SUBNET/24 ! -o ogstun -j MASQUERADE


#iperf3 -B $SUBNET -s -fm &

cp /open5gs/install/etc/open5gs/temp/$COMPONENT_NAME.yaml /open5gs/install/etc/open5gs/upf.yaml

sleep 15
./install/bin/open5gs-upfd
