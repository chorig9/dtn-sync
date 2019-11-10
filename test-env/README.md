#Environment file structure
```
{
	"networks": 
	[
		{
			"id":0,
			"ip4_prefix":"10.83.0.0/16"
		}
		...
	],
	"nodes":
	[
		{
			"id":0,
			"networks":[
				0, ...
			]
		}
                ...
	]
}
```
###networks
List of all networks in the test. Each network is separate switch in the network emulator.
Each network contains of:
* id - id of the network
* either ip4_prefix or ip6_prefix - network prefix **with** network mask

###nodes
List of all nodes in tested environment. Each node is PC node in the network emulator.
Each node contains of:
* id - id of the node
* networks - list of network's ids to which node is connected, or will be connected in the test

## Running tests
Running core daemon is required (run /etc/init.d/core-daemon start)
