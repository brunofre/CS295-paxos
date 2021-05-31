import socket
import random
import threading
from messages import *


def print_debug(msg):
    print("DEBUG:", msg)


class Coordinator:

    # each replica is a pubkey -> {ip, port, debug_socket} where port is UDP and socket is TCP
    replicas = {}

    def __init__(self, ip, listening_port):
        # opens tcp socket and spans threads
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.bind((ip, listening_port))
        self.s.listen(5)

        self.replicaslock = threading.Lock()  # makes sure replicas[] is not modified

    def start(self):
        while True:
            (clientsocket, address) = self.s.accept()
            t = threading.Thread(target=self.client_thread,
                                 args=(self, clientsocket,))
            t.start()

    def client_thread(self, t, c):
        while True:
            msg = CoordinatorMessage.receive(c)
            if msg is None:
                c.close()
                break

            if msg.TYPE == PeerInfo.TYPE:  # this is a new peer
                # sends prev replicas to this one
                self.replicaslock.acquire()  # released in spread_new_replica below
                for vk, r in self.replicas.items():
                    pinfo = PeerInfo(vk, r["ip"], r["port"])
                    pinfo.send(c)
                self.replicas[msg.vk] = {
                    "ip": msg.ip, "port": msg.port, "attack": msg.attack, "debug_socket": c, "debugthread": t}
                # tell new node that is all we have by sending his info back
                msg.send(c)
                # now let older replicas know of the new one
                self.spread_new_replica(msg)
            elif msg.TYPE == DebugInfo.TYPE:  # just a debug message, print it
                print_debug(msg.vk[:10] + " " + msg.msg)
            else:
                pass

    def spread_new_replica(self, msg):
        for vk, rep in self.replicas.items():
            if vk != msg.vk:
                s = rep["debug_socket"]
                msg.send(s)
        self.replicaslock.release()

    # picks a random replica and tells it to try to propagate this value
    def random_propagate(self, pos, value):
        who = random.choice(list(self.replicas.keys()))
        for vk, replica in self.replicas.items():
            if replica["attack"] == Attack.CONSISTENCY:
                who = vk
            if replica["attack"] == Attack.AVILABILITY:
                while who == vk:
                    who = random.choice(list(self.replicas.keys()))
            if replica["attack"] == Attack.PREPARE_PHASE_1:
                msg = CoordinatorPropagateMessage(pos, value)
                msg.send(self.replicas[vk]["debug_socket"])
        print_debug(
            f"Coordinator telling {who} to propagate {value} at pos {pos}")
        msg = CoordinatorPropagateMessage(pos, value)
        msg.send(self.replicas[who]["debug_socket"])
