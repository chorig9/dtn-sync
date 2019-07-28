import random
import string
import subprocess
import os

def generate_random_name(length = 8):
    letters = string.ascii_letters + string.digits
    return ''.join(random.choice(letters) for i in range(length))

def get_tmp_folder():
    dir = os.path.join("/tmp", generate_random_name())
    os.mkdir(dir)

    return dir

def get_tmp_filename():
    path = os.path.join("/tmp", generate_random_name())
    return path

def run_command(command, env_vars):
    for env in env_vars:
        name, value = env
        os.environ[name] = value

    print(command)

    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    std, stderr = process.communicate()

    for env in env_vars:
        name, value = env
        os.environ[name] = ""

    if stderr:
        raise Exception(stderr)

    return std
