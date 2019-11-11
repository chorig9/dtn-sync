from env_parser import EnvParser

from core import load_logging_config
from core.emulator.coreemu import CoreEmu
from core.emulator.emudata import IpPrefixes
from core.emulator.enumerations import NodeTypes, EventTypes

import os, shutil


class Env():
    def __init__(self, env_config, silent=True):
        if not silent:
            load_logging_config()

        self.envParser = EnvParser(env_config)

        if self.envParser.ip4_prefix:
            self.prefix = IpPrefixes(ip4_prefix=self.envParser.ip4_prefix)
        else:
            self.prefix = IpPrefixes(ip6_prefix=self.envParser.ip6_prefix)

        self.nodes = {}  # pc nodes
        self.networks = []  # switches nodes

        # create emulator instance for creating sessions and utility methods
        self.coreemu = CoreEmu()
        self.session = self.coreemu.create_session()

        # must be in configuration state for nodes to start, when using "node_add" below
        self.session.set_state(EventTypes.CONFIGURATION_STATE)

        # create nodes
        for node in self.envParser.nodes:
            self.nodes[int(node["id"])] = {"obj": self.session.add_node(_type=NodeTypes.DEFAULT), "nets": [],
                                           "ip": None, "curr_net": None}

        # create networks
        for net in self.envParser.networks:
            self.networks.append(self.session.add_node(_type=NodeTypes.SWITCH))
            for node in net["nodes"]:
                interface = self.prefix.create_interface(self.nodes[node["id"]]["obj"],
                                                         name=self.envParser.dev_prefix + str(net["id"]))
                self.nodes[node["id"]]["ip"] = self.prefix.ip4_address(self.nodes[node["id"]]["obj"])
                self.session.add_link(self.nodes[node["id"]]["obj"].id, self.networks[-1].id, interface_one=interface)
                self.nodes[node["id"]]["nets"].append({
                    "net": net["id"]
                })
        # certs
        shutil.rmtree('certs', True)
        self.__create_root_ca()
        for node in self.nodes:
            self.__create_node_cert(node)
        # instantiate session
        self.start()

    def get_node_ip(self, node):
        return self.nodes[node]["ip"]

    def run_command(self, node, command, wait=True):
        print(*command)
        self.nodes[node]["obj"].client.cmd(command, wait)

    def run_icommand(self, node, command):
        self.nodes[node]["obj"].client.icmd(command)

    def run_terminal(self, node):
        self.nodes[node]["obj"].client.term()

    def change_net(self, node, net):
        self.nodes[node]["obj"].cmd(
            ["ip", 'l', 'set', self.envParser.dev_prefix + str(self.nodes[node]['curr_net']), 'down'])
        self.nodes[node]["obj"].cmd(["ip", 'l', 'set', self.envParser.dev_prefix + str(net), 'up'])
        self.nodes[node]["curr_net"] = net

    '''options:
        delay TIME [ JITTER [CORRELATION]] [distribution {uniform|normal|pareto|paretonormal} ]
        corrupt PERCENT [CORRELATION]
        duplicate PERCENT [CORRELATION]
        loss random PERCENT [CORRELATION]
        loss state P13 [P31 [P32 [P23 P14]]
        loss gemodel PERCENT [R [1-H [1-K]]
        reorder PRECENT [CORRELATION] [ gap DISTANCE ]
   '''

    def add_net_params(self, nodes, net, params):
        for node in nodes:
            for param in params:
                self.nodes[node]["obj"].client.cmd(
                    ["tc", 'qdisc', 'add', 'dev', self.envParser.dev_prefix + str(net), 'root', 'netem', param] +
                    params[param])
        return

    '''
        Use add on first setting a params, later use set
    '''

    def set_net_params(self, nodes, net, params):
        for node in nodes:
            for param in params:
                self.nodes[node]["obj"].cmd(
                    ["tc", 'qdisc', 'change', 'dev', self.envParser.dev_prefix + str(net), 'root', 'netem', param] +
                    params[param])
        return

    def start(self):
        self.session.instantiate()
        for node in self.nodes.values():
            for net in node['nets']:
                node["obj"].cmd(["ip", 'l', 'set', self.envParser.dev_prefix + str(net['net']), 'down'])
            node["obj"].cmd(["ip", 'l', 'set', self.envParser.dev_prefix + str(node['nets'][0]['net']), 'up'])
            node['curr_net'] = node['nets'][0]['net']



    def finish(self):
        # remove certs
        shutil.rmtree('certs')
        # shutdown session
        self.coreemu.shutdown()

    # XXX: every cert's related things are store in "certs" directory just for now
    def __create_root_ca(self):
        try:
            os.mkdir('certs')
        except FileExistsError:
            pass
        os.system("openssl genrsa -out certs/rootCA.key 4096")
        os.system(
            "openssl req -x509 -new -nodes -key certs/rootCA.key -sha256 -days 1024 -subj \"/C=PL/ST=CA/O=DTN_TEST_ENV, Inc./CN=ROOT_CA\" -out certs/rootCA.crt")

    def __create_node_cert(self, nodeId):
        os.system("openssl genrsa -out certs/node" + str(nodeId) + ".key 2048")
        os.system("openssl req -new -sha256 -key certs/node" + str(
            nodeId) + ".key -subj \"/C=PL/ST=CA/O=DTN_TEST_ENV, Inc./CN=node" + str(
            nodeId) + "\" -out certs/node" + str(nodeId) + ".csr")
        os.system("openssl x509 -req -in certs/node" + str(
            nodeId) + ".csr -CA certs/rootCA.crt -CAkey certs/rootCA.key -CAcreateserial -out certs/node" + str(
            nodeId) + ".crt -days 500 -sha256")
