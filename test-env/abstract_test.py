from abc import ABC
from env import Env
import json


class AbstractTest(ABC):
    def __init__(self, env_file=None):
        if env_file:
            with open(env_file) as f:
                self.config = json.load(f)
        else:
            self.loadConfig()

        self.env = Env(self.config)

    """
    Override this method if your test use local config
    """

    def load_config(self):
        self.config = \
            {
                "config": {
                    "ip4_prefix": "10.83.0.0/16",
                    "dev_prefix": "eth"
                },
                "networks": [
                    {
                        "id": 0,
                    }
                ],
                "nodes": [
                    {
                        "id": 0,
                        "networks": [
                            0
                        ]
                    },
                    {
                        "id": 1,
                        "networks": [
                            0
                        ]

                    },
                    {
                        "id": 2,
                        "networks": [
                            0
                        ]

                    }
                ]
            }
