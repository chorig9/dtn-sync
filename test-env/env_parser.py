class EnvParser:
    def __init__(self, data):
        self.networks = []
        self.nodes = []
        self.ip4_prefix = data['config']["ip4_prefix"] if "ip4_prefix" in data['config'].keys() else None
        self.ip6_prefix = data['config']["ip6_prefix"] if "ip6_prefix" in data['config'].keys() else None
        self.dev_prefix = data['config']['dev_prefix']
        for net in data["networks"]:
            self.networks.append(
                {
                    "id": net["id"],
                    "nodes": []
                }
            )
        for node in data["nodes"]:
            self.nodes.append(node)
            for net in node["networks"]:
                self.networks[net]["nodes"].append(
                    {
                        "id": node["id"]
                    }
                )
