from attack import Attack
from node import Node
from coordinator import Coordinator
import argparse
import threading
import time

parser = argparse.ArgumentParser(prog='Paxos 101')

parser.add_argument("method", help="pick between coordinator, node, debug, attack")
parser.add_argument("--coordip", type=str)
parser.add_argument("--coordport", type=int)
parser.add_argument("--ip", type=str)
parser.add_argument("--port", type=int)
parser.add_argument("--attack", type=str, help="SAFETY,LIVENESS")
parser.add_argument("--middleware", action='count', help="enables middleware against SAFETY and LIVENESS attacks")

args = parser.parse_args()

middleware = args.middleware is not None

if args.method == "node":
    if args.attack:
        attack = getattr(Attack, args.attack)
    else:
        attack = None
    n = Node(args.ip, args.port, args.coordip, args.coordport, attack=attack, middleware=middleware)
    n.start()
elif args.method == "coordinator":
    c = Coordinator(args.ip, args.port)
    c.start()
elif args.method == "debug":
    print("Starting debugging")
    localhost = "127.0.0.1"
    coordinator_port = 18999
    nodes_port = 19000
    threads = []

    coord = Coordinator(localhost, coordinator_port)
    t = threading.Thread(target=coord.start)
    threads.append(t)

    attack = getattr(Attack, args.attack)
    
    nodes = []
    for i in range(3):
        if attack is not None and i == 0:
            n = Node(localhost, nodes_port+i, localhost,
                     coordinator_port, attack=attack, middleware=middleware)
        else:
            n = Node(localhost, nodes_port+i, localhost,
                     coordinator_port, middleware=middleware)
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
        time.sleep(10)
    # to do: get user input

    # for x in threads:
    #    x.join()
