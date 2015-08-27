What's docker-pseudo-dc
==========
Dockerコンテナを活用して、DataCenter側Tenantネットワークの疑似環境を構築するものです. 


Environment
==========
Ubuntu Server版を推奨とします.

	$ cat /etc/lsb-release 
	DISTRIB_ID=Ubuntu
	DISTRIB_RELEASE=14.04
	DISTRIB_CODENAME=trusty
	DISTRIB_DESCRIPTION="Ubuntu 14.04.2 LTS"

Dockerコンテナで構成されるTenantネットワークと外部環境と通信するために、eth2, eth3のインタフェースを前提とします.

	$ ip link
        ...
	4: eth2: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UP mode DEFAULT group default qlen 1000
	    link/ether 00:0c:29:74:14:4a brd ff:ff:ff:ff:ff:ff
	5: eth3: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc pfifo_fast state UP mode DEFAULT group default qlen 1000
	    link/ether 00:0c:29:74:14:54 brd ff:ff:ff:ff:ff:ff


Installation
==========
### リポジトリ情報
Githubよりリポジトリ情報を取得します.

	$ git clone https://github.com/ttsubo/docker-pseudo-dc.git

### インストール開始
ルート権限でdockerパッケージ類をインストールします.

	$ cd docker-pseudo-dc
	$ sudo apt-get install python-dev
	$ sudo apt-get install python-paramiko
	$ sudo pip install -r requirements.txt
	$ sudo python ./pseudo-dc.py install


### インストール結果確認
グループ"docker"への反映を有効にするため、再ログインします.

	$ docker version
	Client version: 1.7.0
	Client API version: 1.19
	Go version (client): go1.4.2
	Git commit (client): 0baf609
	OS/Arch (client): linux/amd64
	Server version: 1.7.0
	Server API version: 1.19
	Go version (server): go1.4.2
	Git commit (server): 0baf609
	OS/Arch (server): linux/amd64


Dockerイメージを確認します.

	$ docker images
	REPOSITORY          TAG                 IMAGE ID            CREATED             VIRTUAL SIZE
	ubuntu              14.04.2             63e3c10217b8        3 weeks ago         188.4 MB


Quick Start
===========
### Dockerコンテナ起動
DataCenter側Tenantネットワークの疑似環境を構築します.

	$ sudo python pseudo-dc.py start

	(...snip)


Dockerコンテナ実行状況を確認します.

	$ docker ps

	(...snip)
	272630f0b414        ubuntu              "bash"              58 minutes ago      Up 58 minutes                           host_009_2009       
	e439e48e39cf        ubuntu              "bash"              58 minutes ago      Up 58 minutes                           host_008_2008       
	84fbee041583        ubuntu              "bash"              58 minutes ago      Up 58 minutes                           host_007_2007       
	0068e23ae89d        ubuntu              "bash"              58 minutes ago      Up 58 minutes                           host_006_2006       
	d6316ea0f2df        ubuntu              "bash"              58 minutes ago      Up 58 minutes                           host_005_2005       
	5e94d6cd8f63        ubuntu              "bash"              58 minutes ago      Up 58 minutes                           host_004_2004       
	45ea01479165        ubuntu              "bash"              58 minutes ago      Up 58 minutes                           host_003_2003       
	7bd4ab0f230b        ubuntu              "bash"              58 minutes ago      Up 58 minutes                           host_002_2002       
	7e6fd01b6203        ubuntu              "bash"              58 minutes ago      Up 58 minutes                           host_001_2001 

Linuxブリッジ動作状況を確認します.

	$ brctl show

	(...snip)
	br3610-1		8000.0643928767a7	no		veth0pl17505
	br3610-2		8000.1a12463629fa	no		veth1pl17505
	br3610-3		8000.5a681fb7fd91	no		veth2pl17505
	br3610-4		8000.fe330662b497	no		veth3pl17505
	br3610-5		8000.6eac4152508c	no		veth4pl17505
	br3611-1		8000.3e6aea49544f	no		veth0pl18407
	br3611-2		8000.d60abd87f45d	no		veth1pl18407
	br3611-3		8000.6e42594e14b0	no		veth2pl18407
	br3611-4		8000.82766c58e360	no		veth3pl18407
	br3611-5		8000.86e3b1fa7686	no		veth4pl18407
	vnic1		8000.000c2974144a	no		eth2
	vnic2		8000.000c29741454	no		eth3


### Dockerコンテナへアクセス
例えば、dockerコンテナ"host_001_2001"にアクセスして、ネットワーク情報を確認してみます.

	$ docker exec -it host_001_2001 bash
	# ip route
	default via 130.1.0.1 dev vnic1.2001 
	130.1.0.0/24 dev vnic1.2001  proto kernel  scope link  src 130.1.0.4 
	130.1.0.0/24 dev vnic2.2001  proto kernel  scope link  src 130.1.0.5 
	140.1.1.0/24 dev eth0  proto kernel  scope link  src 140.1.1.1 
	140.1.2.0/24 dev eth1  proto kernel  scope link  src 140.1.2.1 
	140.1.3.0/24 dev eth2  proto kernel  scope link  src 140.1.3.1 
	140.1.4.0/24 dev eth3  proto kernel  scope link  src 140.1.4.1 
	140.1.5.0/24 dev eth4  proto kernel  scope link  src 140.1.5.1 
	# exit




### Dockerコンテナ停止
Dockerコンテナを停止します.

	$ sudo python pseudo-dc.py stop

	(...snip)


Dockerコンテナが起動していないことを確認します.

	$ docker ps
	CONTAINER ID        IMAGE               COMMAND             CREATED             STATUS              PORTS

