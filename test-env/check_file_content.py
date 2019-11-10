import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-f", "--file", required=True)
parser.add_argument("-c", "--content", required=True)

args = parser.parse_args()

with open(args.file, 'r') as f:
    content = f.read()
    if content != args.content:
        raise Exception("Should be: " + args.content + "\nIs: " + content + "\n")