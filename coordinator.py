import struct
import socket
import secrets
import threading
from messages import *

def debugprint(msg):
    print("DEBUG:", msg)

class Coordinator:

    # each replica is a pubkey -> {ip, port, debugsocket} where port is UDP and socket is TCP
    replicas = {}

    def __init__(self, ip, listening_port):
        # opens tcp socket and spans threads
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.bind((ip, listening_port))
        self.s.listen(5)

        self.replicaslock = threading.Lock() # makes sure replicas[] is not modified

    def start(self):
        while True:
            (clientsocket, address) = self.s.accept()
            t = threading.Thread(target=self.client_thread, args=(self,clientsocket,))
            t.start()
            
    def client_thread(self, t, c):

        while True:
            msg = MessageNoSignature.recv_with_tcp(c)
            if msg is None:
                c.close()
                break
            
            if msg.TYPE == "peerinfo": # this is a new peer
                # sends prev replicas to this one
                self.replicaslock.acquire() # released in spread_new_replica below
                for vk, r in self.replicas.items():
                    pinfo = PeerInfo(vk, r["ip"], r["port"])
                    pinfo.send_with_tcp(c)
                self.replicas[msg.vk] = {"ip":msg.ip, "port":msg.port, "debugsocket":c, "debugthread":t}
                # tell new node that is all we have by sending his info back
                msg.send_with_tcp(c)
                # now let older replicas know of the new one
                self.spread_new_replica(msg)
            elif msg.TYPE == "debug": # just a debug message, print it
                debugprint(msg.vk[:10] + " " + msg.msg)
            else:
                pass

    def spread_new_replica(self, msg):
        for vk, rep in self.replicas.items():
            if vk != msg.vk:
                s = rep["debugsocket"]
                msg.send_with_tcp(s)
        self.replicaslock.release()

    # picks a random replica and tells it to try to propagate this value
    def random_propagate(self, value):
        value = str(value)
        who = secrets.choice(list(self.replicas.keys()))
        debugprint("Coordinator telling " + who + " to propagate " + value)
        msg = ControllerPropagateMessage(value)
        msg.send_with_tcp(self.replicas[who]["debugsocket"])

