# TODO: and app import and run on every node


from env_parser import EnvParser

from core import load_logging_config
from core.emulator.coreemu import CoreEmu
from core.emulator.emudata import IpPrefixes
from core.emulator.enumerations import NodeTypes, EventTypes


class Env():
    def __init__(self, env_config, silent=False):
        if not silent:
            load_logging_config()

        self.envParser = EnvParser(env_config)

        self.nodes = {}     #pc nodes
        self.networks = []  #switches nodes 
        self.prefixes = []  #IpPrefixes objects

        # create emulator instance for creating sessions and utility methods
        self.coreemu = CoreEmu()
        self.session = self.coreemu.create_session()

        # must be in configuration state for nodes to start, when using "node_add" below
        self.session.set_state(EventTypes.CONFIGURATION_STATE)
        
        # create nodes
        for node in self.envParser.nodes:
            self.nodes[int(node["id"])] = { "obj":self.session.add_node(_type=NodeTypes.DEFAULT), "ips":[] }
        
        # create networks
        for net in self.envParser.networks:        
            if net["ip4_prefix"]:            
                self.prefixes.append(IpPrefixes(ip4_prefix=net["ip4_prefix"]))
            else:
                self.prefixes.append(IpPrefixes(ip6_prefix=net["ip6_prefix"]))
            self.networks.append(self.session.add_node(_type=NodeTypes.SWITCH))
            for node in net["nodes"]:
                interface = self.prefixes[-1].create_interface(self.nodes[node["id"]]["obj"])
                self.session.add_link(self.nodes[node["id"]]["obj"].id, self.networks[-1].id, interface_one=interface)
                self.nodes[node["id"]]["ips"].append({
                    "net": net["id"],               
                    "ip":self.prefixes[-1].ip4_address(self.nodes[node["id"]]["obj"])
                })

        # instantiate session
        self.session.instantiate()

    def get_node_ips(self, node):
        return self.nodes[node]["ips"]

    def run_command(self, node, command):
        self.nodes[node]["obj"].cmd(command)

    def run_icommand(self, node, command):
        self.nodes[node]["obj"].client.icmd(command)

    def finish(self):
        # shutdown session
        self.coreemu.shutdown()
