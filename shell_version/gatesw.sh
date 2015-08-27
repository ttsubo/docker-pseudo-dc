#!/bin/sh

check_user() {
    if [ `whoami` = "root" ]; then
        echo "Super user cannot execute! Please execute as non super user"
        exit 2
    fi
}

add_bridge() {
    local bridge_name=$1
    sudo brctl addbr $bridge_name
    sudo ip link set $bridge_name up
}

add_host() {
    local host_name=$1
    docker run --name $host_name --privileged=True --net=none -h $host_name -itd ubuntu /bin/bash
    add_netns $host_name
}

add_gw(){
    local host_name=$1
    local gw=$2
    docker exec $host_name route add -net 0.0.0.0/0 gw $gw
}

add_link_for_tenant() {
    local bridge=$1
    local nic=$2
    local host=$3
    local ip=$4
    sudo pipework $bridge -i $nic $host $ip
}

add_link_for_wan(){
    local bridge=$1
    local vlan=$2
    local host=$3
    local ip=$4
    sudo ip link add link $bridge name $bridge.$vlan type vlan id $vlan
    sudo ip link set $bridge.$vlan up
    sudo ip link set $bridge.$vlan netns $host up
    sudo ip netns exec $host ip addr add $ip dev $bridge.$vlan
}

add_netns() {
    local host_name=$1
    local pid=$(docker inspect -f '{{.State.Pid}}' $host_name)
    if [ -f /var/run/netns ]; then
        sudo mkdir /var/run/netns
    fi
    sudo ln -s /proc/$pid/ns/net /var/run/netns/$host_name
}

delete_bridge() {
    local name=$1
    local sysfs_name=/sys/class/net/$name
    if [ -e $sysfs_name ]; then
        sudo ifconfig $name down
	sudo brctl delbr $name
    fi
}

del_all_netns() {
    docker rm -f $(docker ps -qa)
    sudo rm -f /var/run/netns/*
}

case "$1" in
    start)
        # deploy bridge
        add_bridge vnic1
        add_bridge vnic2
        # deploy Customer202
        add_host Customer202
        add_link_for_wan vnic1 2804 Customer202 30.200.112.4/26
        add_link_for_wan vnic2 2804 Customer202 30.200.112.5/26
        add_link_for_tenant br101 eth1 Customer202 40.200.112.1/29
        add_link_for_tenant br102 eth2 Customer202 40.201.112.1/29
        add_gw Customer202 30.200.112.1
        # deploy Customer207
        add_host Customer207
        add_link_for_wan vnic1 2805 Customer207 30.200.117.4/26
        add_link_for_wan vnic2 2805 Customer207 30.200.117.5/26
        add_link_for_tenant br103 eth1 Customer207 40.200.117.1/29
        add_link_for_tenant br104 eth2 Customer207 40.201.117.1/29
        add_gw Customer207 30.200.117.1
        # deploy Customer209
        add_host Customer209
        add_link_for_wan vnic1 2806 Customer209 30.200.119.4/26
        add_link_for_wan vnic2 2806 Customer209 30.200.119.5/26
        add_link_for_tenant br105 eth1 Customer209 40.200.119.1/29
        add_link_for_tenant br106 eth2 Customer209 40.201.119.1/29
        add_gw Customer209 30.200.119.1


        # add bridge interface
        sudo brctl addif vnic1 eth2
        sudo brctl addif vnic2 eth3
	;;
    stop)
        del_all_netns
	delete_bridge br101
	delete_bridge br102
	delete_bridge br103
	delete_bridge br104
	delete_bridge br105
	delete_bridge br106
        delete_bridge vnic1
        delete_bridge vnic2
	;;
    install)

        sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 36A1D7869245C8950F966E92D8576A8BA88D21E9
        sudo sh -c "echo deb https://get.docker.io/ubuntu docker main > /etc/apt/sources.list.d/docker.list"
        sudo apt-get update
        sudo apt-get install -y --force-yes lxc-docker-1.7.0
        sudo ln -sf /usr/bin/docker.io /usr/local/bin/docker
        sudo gpasswd -a `whoami` docker
        sudo wget https://raw.github.com/jpetazzo/pipework/master/pipework -O /usr/local/bin/pipework
        sudo chmod 755 /usr/local/bin/pipework
        sudo apt-get install -y --force-yes iputils-arping bridge-utils tcpdump lv ethtool python
        sudo docker pull ubuntu:14.04.2
        sudo mkdir -p /var/run/netns
        ;;
    *)
        echo "Usage: ryu-docker-handson {start|stop|install}"
        exit 2
        1;
esac
