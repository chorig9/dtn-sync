from abstract_test import AbstractTest


class BasicTests(AbstractTest):
	def test1(self):
		self.env.run_icommand(1, ["ping", "-c", "2", self.env.get_node_ips(0)[0]["ip"]])

		self.env.run_icommand(0, ["iperf", "-s", "-D"])
		self.env.run_icommand(2, ["iperf", "-t", "10", "-c", self.env.get_node_ips(0)[0]["ip"]])

		self.env.finish()

class OutOfOrderPatchTests(AbstractTest):
	TEST_PORT = "1234"
	DTN_SOURCE_DIR = "/home/igor/Projects/dtn-sync/src/main.py"

	def test1(self):
		self.env.run_icommand(0, ["python3", OutOfOrderPatchTests.DTN_SOURCE_DIR, "-p", OutOfOrderPatchTests.TEST_PORT, "-d", "/tmp/test_node0"])
		self.env.run_icommand(1, ["python3", OutOfOrderPatchTests.DTN_SOURCE_DIR, "-p", OutOfOrderPatchTests.TEST_PORT, "-d", "/tmp/test_node1"])

		self.env.run_icommand(2, ["echo", "TEST1", ">", "/tmp/test_node0/file1"])

		self.env.run_icommand(2, ["cat", "/tmp/test_node0/file1"])
		self.env.run_icommand(2, ["cat", "/tmp/test_node1/file1"])

		self.env.finish()


if __name__ == "__main__":
	#basic_tests = BasicTests("c3.json")
	#basic_tests.test1()

	out_of_order_patch_tests = OutOfOrderPatchTests("c3.json")
	out_of_order_patch_tests.test1()
