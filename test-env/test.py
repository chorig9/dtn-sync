from abstract_test import AbstractTest


class BasicTests(AbstractTest):
	def test1(self):
		self.env.run_icommand(1, ["ping", "-c", "2", self.env.get_node_ips(0)[0]["ip"]])

		self.env.run_icommand(0, ["iperf", "-s", "-D"])
		self.env.run_icommand(2, ["iperf", "-t", "10", "-c", self.env.get_node_ips(0)[0]["ip"]])

		self.env.finish()


if __name__ == "__main__":
	basic_tests = BasicTests("c3.json")
	basic_tests.test1()
