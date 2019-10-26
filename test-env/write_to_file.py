import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-f", "--file", required=True)
parser.add_argument("-c", "--content", required=True)

args = parser.parse_args()

with open(args.file, 'w') as f:
    f.write(args.content)