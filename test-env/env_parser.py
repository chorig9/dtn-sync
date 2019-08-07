# TODO: add node's connections


class EnvParser:
    def __init__(self, data):
        self.networks = []
        self.nodes = []
        for net in data["networks"]:
            self.networks.append(
                {
                    "id": net["id"],
                    "ip4_prefix": net["ip4_prefix"] if "ip4_prefix" in net else None,
                    "ip6_prefix": net["ip6_prefix"] if "ip6_prefix" in net else None,
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
