import os.path
from fabric.api import local
from netaddr.ip import IPNetwork, IPAddress

class Container(object):
    def __init__(self, name, vlan, bridges, conn_ip, tenant_ip, tenant_num):
        self.name = name
        self.image = 'ubuntu'
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



if __name__ == '__main__':

    vnic1 = Bridge(name='vnic1')
    vnic2 = Bridge(name='vnic2')

    bridges = ['vnic1', 'vnic2']

    host1 = Container('host1', 2001, bridges, '30.1.0.0/24', '40.1.0.0/24', 5)
    host2 = Container('host2', 2002, bridges, '30.2.0.0/24', '40.2.0.0/24', 5)
    host3 = Container('host3', 2003, bridges, '30.3.0.0/24', '40.3.0.0/24', 5)
    hosts = [host1, host2, host3]

    [host.run() for host in hosts]
