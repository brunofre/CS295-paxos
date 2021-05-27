from node import Node
from coordinator import Coordinator
import argparse
import threading
import time

parser = argparse.ArgumentParser(prog='Paxos 101')

# to do, parse arguments

args = parser.parse_args()


if __name__ == "__main__":
    print("Starting debugging")
    localhost = "127.0.0.1"
    coordport = 18999
    nodesport = 19000
    threads = []
    t = threading.Thread(target=Coordinator, args=(localhost, coordport,))
    threads.append(t)

    for i in range(10):
        t = threading.Thread(target=Node, args=(localhost, nodesport+i, localhost, coordport,))
        threads.append(t)

    for t in threads:
        t.setDaemon(True)
        t.start()
        time.sleep(1)
        

    # to do: get user input

    for x in threads:
        x.join()



    
