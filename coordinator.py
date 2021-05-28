import struct
import socket
import threading
from messages import *

class Coordinator:

    # each replica is a pubkey -> {ip, port, debugsocket} where port is UDP and socket is TCP
    replicas = {}

    def __init__(self, ip, listening_port):
        # opens tcp socket and spans threads
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.bind((ip, listening_port))
        self.s.listen(5)

        while True:
            (clientsocket, address) = self.s.accept()
            t = threading.Thread(target=self.client_thread, args=(self,clientsocket,))
            t.start()
            
    def client_thread(self, t, c):

        print("Coordinator opening node debug thread")
        while True:
            msg = MessageNoSignature.recv_with_tcp(c)
            if msg is None:
                c.close()
                break
            
            if msg.TYPE == "peerinfo": # this is a new peer
                # first gets replica info from the msg
                self.replicas[msg.vk] = {"ip":msg.ip, "port":msg.port, "debugsocket":c, "debugthread":t}                
                # then sends prev replicas to this one
                for vk, r in self.replicas.items():
                    pinfo = PeerInfo(vk, r["ip"], r["port"])
                    pinfo.send_with_tcp(c)
                # now let older replicas know of the new one
                self.spread_new_replica(msg)
            elif msg.TYPE == "debug": # just a debug message, print it
                print("DEBUG", msg.vk, msg.msg)
            else:
                pass

    def spread_new_replica(self, msg):
        for vk, rep in self.replicas.items():
            if vk != msg.vk:
                s = rep["debugsocket"]
                msg.send_with_tcp(s)
