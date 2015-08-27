import os.path
from fabric.api import local
from netaddr.ip import IPNetwork, IPAddress
from optparse import OptionParser
import sys

host_serial_number = 0

def install_docker_and_tools():
    print "start install packages of test environment."
    local("apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys "
          "36A1D7869245C8950F966E92D8576A8BA88D21E9", capture=True)
    local('sh -c "echo deb https://get.docker.io/ubuntu docker main > /etc/apt/sources.list.d/docker.list"',
          capture=True)
    local("apt-get update", capture=True)
    local("apt-get install -y --force-yes lxc-docker-1.7.0 bridge-utils tcpdump", capture=True)
    local("ln -sf /usr/bin/docker.io /usr/local/bin/docker", capture=True)
    local("gpasswd -a `whoami` docker", capture=True)
    local("wget https://raw.github.com/jpetazzo/pipework/master/pipework -O /usr/local/bin/pipework",
          capture=True)
    local("chmod 755 /usr/local/bin/pipework", capture=True)
    local("docker pull ubuntu:14.04.2", capture=True)
    local("mkdir -p /var/run/netns", capture=True)

class Container(object):
    def __init__(self, name, vlan, bridges, conn_ip, tenant_ip, tenant_num):
        self.name = name
        self.image = 'ubuntu:14.04.2'
        self.vlan = vlan
        self.bridges = bridges
        self.conn_ip = conn_ip
        self.tenant_ip = tenant_ip
        self.tenant_num = tenant_num

        if self.name in get_containers():
            print ("### Delete connertainer {0} ###".format(self.name))
            self.stop()

    def run(self):
        c = CmdBuffer(' ')
        c << "docker run --privileged=true --net=none"
        c << "--name {0} -h {1} -itd {1}".format(self.name, self.image)
        c << "bash"

        print ("### Create connertainer {0} ###".format(self.name))
        self.id = local(str(c), capture=True)
        self.add_netns()
        self.is_running = True
        self.add_link_for_wan(self.name, self.vlan, self.bridges, self.conn_ip)
        self.add_link_for_tenant(self.name, self.vlan, self.tenant_ip, self.tenant_num)
        self.add_gw(self.conn_ip)
        return 0

    def add_gw(self, conn_ip):
        subnet = IPNetwork(conn_ip)
        ipaddr = subnet.ip + 1
        vip = str(ipaddr)

        c = CmdBuffer(' ')
        c << "docker exec {0}".format(self.name)
        c << "route add -net 0.0.0.0/0 gw {0}".format(vip)
        print ("### Add gateway {0} ###".format(self.name))
        return local(str(c), capture=True)

    def add_netns(self):
        if not os.path.isdir("/var/run/netns"):
            local("sudo mkdir /var/run/netns")
        pid = local("docker inspect -f '{{.State.Pid}}' %s"%(self.name), capture=True)
        netns_base = "/proc/{0}/ns/net".format(pid)
        netns_link = "/var/run/netns/{0}".format(self.name)
        if os.path.islink(netns_link):
            local("rm {0}".format(netns_link))
        if os.path.isfile(netns_base):
            local("ln -s {0} {1}".format(netns_base, netns_link), capture=False)

    def add_link_for_wan(self, host, vlan, bridges, conn_ip):
        subnet = IPNetwork(conn_ip)
        act = subnet.ip + 4
        sby = subnet.ip + 5
        mask = subnet.netmask
        act_ip = IPNetwork(str(act) + '/' + str(mask))
        sby_ip = IPNetwork(str(sby) + '/' + str(mask))

        for vnic in bridges:
            if vnic == 'vnic1':
                ipaddress = str(act_ip)
            elif vnic == 'vnic2':
                ipaddress = str(sby_ip)

            print ("### add_link_for_wan for {0} ###".format(vnic))
            local("ip link add link {0} name {0}.{1} type vlan id {1}".format(vnic, vlan))
            local("ip link set {0}.{1} up".format(vnic, vlan))
            local("ip link set {0}.{1} netns {2} up".format(vnic, vlan, host))
            local("ip netns exec {0} ip addr add {1} dev {2}.{3}".format(host, ipaddress, vnic, vlan))

    def add_link_for_tenant(self, host, vlan, tenant_ip, tenant_num):
        for i in range(tenant_num):
            subnet = IPNetwork(tenant_ip)
            ipaddr = subnet.ip + (256 * i) + 1
            mask = subnet.netmask
            prefix = IPNetwork(str(ipaddr) + '/' + str(mask))

            br_name = 'br' + str(vlan) + '-' + str(i+1)
            if_name = 'eth'+str(i)
            self.pipework(br_name, if_name, host, prefix)


    def stop(self):
        local("docker rm -f " + self.name, capture=False)
        self.is_running = False

    def pipework(self, bridge, if_name, host, ip_addr):
        if not self.is_running:
            print ('*** call run() before pipeworking')
            return
        c = CmdBuffer(' ')
        c << "pipework {0}".format(bridge)

        if if_name != "":
            c << "-i {0}".format(if_name)
        else:
            intf_name = "eth1"
        c << "{0} {1}".format(host, ip_addr)
        print ("### add_link_for_tenant {0} ###".format(if_name))
        return local(str(c), capture=True)


class CmdBuffer(list):
    def __init__(self, delim='\n'):
        super(CmdBuffer, self).__init__()
        self.delim = delim

    def __lshift__(self, value):
        self.append(value)

    def __str__(self):
        return self.delim.join(self)


class Bridge(object):
    def __init__(self, name):
        self.name = name

        if self.name in get_bridges():
            self.delete()

        print ("### Create bridge {0} ###".format(self.name))
        local("ip link add {0} type bridge".format(self.name), capture=False)
        local("ip link set up dev {0}".format(self.name), capture=False)


    def delete(self):
        print ("### Delete bridge {0} ###".format(self.name))
        local("ip link set down dev {0}".format(self.name), capture=False)
        local("ip link delete {0} type bridge".format(self.name), capture=False)


def get_bridges():
    return local("brctl show | awk 'NR > 1{print $1}'",
                 capture=True).split('\n')

def get_containers():
    output = local("docker ps -a | awk 'NR > 1 {print $NF}'", capture=True)
    if output == '':
        return []
    return output.split('\n')

def create_prefix(bridges, vlan_init, vfw_prefix_init, local_prefix_init, num):
    global host_serial_number
    hosts = []

    for current in range(1, num+1):
        host_serial_number += 1
        if current == 1:
            vlan = vlan_init
            vfw_prefix = vfw_prefix_init
            local_prefix = local_prefix_init
        else:
            vlan += 1
            vfw_subnet = IPNetwork(vfw_prefix)
            vfw_ipaddr = vfw_subnet.ip + 256 * 256
            vfw_mask = vfw_subnet.netmask
            vfw_prefix = IPNetwork(str(vfw_ipaddr) + '/' + str(vfw_mask))

            local_subnet = IPNetwork(local_prefix)
            local_ipaddr = local_subnet.ip + 256 * 256
            local_mask = local_subnet.netmask
            local_prefix = IPNetwork(str(local_ipaddr) + '/' + str(local_mask))

        host = "host_%03d_%03d"%(host_serial_number, vlan)
        hostname = Container(host, vlan, bridges, vfw_prefix, local_prefix, 5)
        hosts.append(hostname)

    [host.run() for host in hosts]

def create_tenant():
    vnic1 = Bridge(name='vnic1')
    vnic2 = Bridge(name='vnic2')
    bridges = ['vnic1', 'vnic2']

    create_prefix(bridges, 2001, '130.1.0.0/24', '140.1.1.0/24', 396)
    create_prefix(bridges, 2601, '132.89.0.0/24', '142.89.1.0/24', 60)
    create_prefix(bridges, 2901, '133.133.0.0/24', '143.133.1.0/24', 102)
    create_prefix(bridges, 3501, '135.221.0.0/24', '145.221.1.0/24', 30)
    create_prefix(bridges, 3600, '136.64.0.0/24', '146.64.1.0/24', 12)

    local("brctl addif vnic1 eth2", capture=True)
    local("brctl addif vnic2 eth3", capture=True)



if __name__ == '__main__':
    parser = OptionParser(usage="usage: %prog [install|start|stop|")
    options, args = parser.parse_args()

    if len(args) == 0:
        sys.exit(1)
    elif args[0] == 'install':
        install_docker_and_tools()
    elif args[0] == 'start':
        create_tenant()
    elif args[0] == 'stop':
        for ctn in get_containers():
            local("docker rm -f {0}".format(ctn), capture=True)

        for bridge in get_bridges():
            local("ip link set down dev {0}".format(bridge), capture=True)
            local("ip link delete {0} type bridge".format(bridge), capture=True)

