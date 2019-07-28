import random
import string
import os

def generate_random_name(length = 8):
    letters = string.ascii_letters + string.digits
    return ''.join(random.choice(letters) for i in range(length))

def get_tmp_folder():
    dir = os.path.join("/tmp", generate_random_name())
    os.mkdir(dir)

    return dir

def run_command(self, command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    std, stderr = process.communicate()

    if stderr:
        raise Exception(stderr)

    return std
