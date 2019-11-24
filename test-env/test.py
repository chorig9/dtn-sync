from abstract_test import AbstractTest
import time
import os
import sys
import shutil

sys.path.append(os.path.abspath('../src'))

import utils


class BasicTests(AbstractTest):
    def test1(self):
        self.env.run_icommand(1, ["ping", "-c", "2", self.env.get_node_ip(0)])

        self.env.run_icommand(0, ["iperf", "-s", "-D"])
        self.env.run_icommand(2, ["iperf", "-t", "10", "-c", self.env.get_node_ip(0)])

        self.env.finish()

class PatchTests(AbstractTest):
	TEST_PORT = "1234"
	DTN_SOURCE_DIR = os.path.dirname(os.path.abspath(__file__)) + "/.."

	def node_dir_path(self, node):
		return "/tmp/test_node%d" % node

	def node_log_file(self, node):
		return "/tmp/node%d_out.txt" % node

	def node_name(self, node):
		return "CoreNode%d" % (node + 1)

	def setup_dirs(self):
		try:
			shutil.rmtree(self.node_dir_path(0))
			shutil.rmtree(self.node_dir_path(1))
		except Exception as e:
			pass

		os.mkdir(self.node_dir_path(0))
		os.mkdir(self.node_dir_path(1))

	def init_node(self, node):
		self.env.run_command(node, ["python3", 
			PatchTests.DTN_SOURCE_DIR + "/src/main.py",
			"-p", PatchTests.TEST_PORT,
			"-d", self.node_dir_path(node),
			"--stdout", self.node_log_file(node),
			"--log", "debug"],
			False)

	def write_to_file(self, file, content):
		utils.run_command(["python3",
			PatchTests.DTN_SOURCE_DIR + "/test-env/write_to_file.py",
			"-f", file,
			"-c", content])

	def check_file_content(self, file, content):
		utils.run_command(["python3",
			PatchTests.DTN_SOURCE_DIR + "/test-env/check_file_content.py",
			"-f", file,
			"-c", content])

	def test1(self):
		self.setup_dirs()

		self.init_node(0)
		self.init_node(1)

		# XXX: potentially can be replaced with waiting for logs to contain "Started"
		time.sleep(5)

		self.write_to_file(self.node_dir_path(0) + "/file", "TEST1")

		time.sleep(5)

		self.check_file_content(self.node_dir_path(0) + "/file", "TEST1")
		self.check_file_content(self.node_dir_path(1) + "/file", "TEST1")

		self.env.finish()

	def test2(self):
		self.check_file_content(self.node_dir_path(0) + "/file", "TEST1")
		self.check_file_content(self.node_dir_path(1) + "/file", "TEST1")

		self.init_node(0)
		self.init_node(1)

		time.sleep(5)

		self.write_to_file(self.node_dir_path(1) + "/file", "222222")

		time.sleep(5)

		self.check_file_content(self.node_dir_path(0) + "/file", "222222")
		self.check_file_content(self.node_dir_path(1) + "/file", "222222")

		self.env.finish()

	# This test sends patches in this order (from node 0 to node 1):
	# commit3, commit4, commit1, commit2
	def test3(self):
		self.init_node(0)

		self.env.run_command(2, ["python3", 
			PatchTests.DTN_SOURCE_DIR + "/test-env/packet_forwarder.py",
			"-p", PatchTests.TEST_PORT,
			"-s", self.env.get_node_ip(1),
			"-k", "2"],
			False)

		time.sleep(5)

		self.write_to_file(self.node_dir_path(0) + "/out-of-order", "1")
		self.write_to_file(self.node_dir_path(0) + "/out-of-order", "22")

		time.sleep(5)
		
		# Get node 1 up - he will receive first two patches from packet_forwarder
		self.init_node(1)

		time.sleep(5)

		self.write_to_file(self.node_dir_path(0) + "/out-of-order", "333")
		self.write_to_file(self.node_dir_path(0) + "/out-of-order", "4444")

		time.sleep(10)

		self.check_file_content(self.node_dir_path(0) + "/out-of-order", "4444")
		self.check_file_content(self.node_dir_path(1) + "/out-of-order", "4444")

		self.env.finish()

	def test4(self):
		self.check_file_content(self.node_dir_path(0) + "/out-of-order", "4444")
		self.check_file_content(self.node_dir_path(1) + "/out-of-order", "4444")

		self.init_node(1)

		self.env.run_command(2, ["python3", 
			PatchTests.DTN_SOURCE_DIR + "/test-env/packet_forwarder.py",
			"-p", PatchTests.TEST_PORT,
			"-s", self.env.get_node_ip(0),
			"-k", "4"],
			False)

		time.sleep(5)

		self.write_to_file(self.node_dir_path(1) + "/out-of-order", "XXXXXX")
		self.write_to_file(self.node_dir_path(1) + "/out-of-order", "A")
		self.write_to_file(self.node_dir_path(1) + "/out-of-order", "B")
		self.write_to_file(self.node_dir_path(1) + "/out-of-order", "POPOPOP")

		time.sleep(5)
		
		self.init_node(0)

		time.sleep(5)

		self.write_to_file(self.node_dir_path(1) + "/out-of-order", "QQQQQQ")
		self.write_to_file(self.node_dir_path(1) + "/out-of-order", "ABABABABABABABAB")

		time.sleep(10)

		self.check_file_content(self.node_dir_path(0) + "/out-of-order", "ABABABABABABABAB")
		self.check_file_content(self.node_dir_path(1) + "/out-of-order", "ABABABABABABABAB")

		self.env.finish()

	# This test sends conflicting patches (from node 0 to node 1):
	# node0:
	# commit1, commit2
	# node1:
	#
	def test5(self):
		self.setup_dirs()

		self.init_node(0)

		self.env.run_command(2, ["python3", 
			PatchTests.DTN_SOURCE_DIR + "/test-env/packet_forwarder.py",
			"-p", PatchTests.TEST_PORT,
			"-s", self.env.get_node_ip(1),
			"-k", "2"],
			False)

		time.sleep(5)

		self.write_to_file(self.node_dir_path(0) + "/conflict", "1")
		self.write_to_file(self.node_dir_path(0) + "/conflict", "22")

		time.sleep(5)
		
		self.init_node(1)

		time.sleep(5)

		# This should trigger packet forwarder
		self.write_to_file(self.node_dir_path(1) + "/conflict", "9999999")

		time.sleep(5)

		self.check_file_content(self.node_dir_path(0) + "/conflict" + self.node_name(0), "22")
		self.check_file_content(self.node_dir_path(0) + "/conflict" + self.node_name(1), "9999999")

		self.check_file_content(self.node_dir_path(1) + "/conflict" + self.node_name(0), "22")
		self.check_file_content(self.node_dir_path(1) + "/conflict" + self.node_name(1), "9999999")

		self.write_to_file(self.node_dir_path(0) + "/conflict" + self.node_name(0), "3333")
		self.write_to_file(self.node_dir_path(0) + "/conflict" + self.node_name(1), "4444")

		time.sleep(5)

		self.check_file_content(self.node_dir_path(0) + "/conflict" + self.node_name(0), "3333")
		self.check_file_content(self.node_dir_path(0) + "/conflict" + self.node_name(1), "4444")

		self.check_file_content(self.node_dir_path(1) + "/conflict" + self.node_name(0), "3333")
		self.check_file_content(self.node_dir_path(1) + "/conflict" + self.node_name(1), "4444")

		self.env.finish()

if __name__ == "__main__":
	basic_tests = BasicTests("c3.json")
	basic_tests.test1()

	patch_tests = PatchTests("c3.json")
	patch_tests.test1()

	patch_tests = PatchTests("c3.json")
	patch_tests.test2()

	patch_tests = PatchTests("c3.json")
	patch_tests.test3()

	patch_tests = PatchTests("c3.json")
	patch_tests.test4()

	patch_tests = PatchTests("c3.json")
	patch_tests.test5()
