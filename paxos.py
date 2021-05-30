from node import Node
from coordinator import Coordinator
import argparse
import threading
import time

parser = argparse.ArgumentParser(prog='Paxos 101')

# to do, parse arguments

args = parser.parse_args()

def attack_on_consistency():
    # create the coord,
    # create two normal replicas
    # create the malicious
    # run it
    pass

def attack_on_liveness():
    pass

if __name__ == "__main__":
    print("Starting debugging")
    localhost = "127.0.0.1"
    coordinator_port = 18999
    nodes_port = 19000
    threads = []

    coord = Coordinator(localhost, coordinator_port)
    t = threading.Thread(target=coord.start)
    threads.append(t)

    nodes = []
    for i in range(3):
        n = Node(localhost, nodes_port+i, localhost, coordinator_port)
        nodes.append(n)
        t = threading.Thread(target=n.start)
        threads.append(t)

    for t in threads:
        t.setDaemon(True)
        t.start()

    time.sleep(3)

    pos = None
    while pos != "stop":
        pos = input("Enter pos to propagate:")
        value = input("Enter value to propagate:")
        coord.random_propagate(pos, value)
        time.sleep(5)
    # to do: get user input

    # for x in threads:
    #    x.join()
