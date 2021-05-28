#!/usr/bin/env python3
import json
import socket
import time
import socketserver
import time
import threading
import base64

from ecdsa.curves import NIST256p
from messages import *
from ecdsa import SigningKey


class Node:
    def __init__(self, host, port, server_ip, server_port, nodes=None):
        self.host, self.port = host, port
        self.server_ip, self.server_port = server_ip, server_port
        self.nodes = nodes # dict vk -> {ip, port, status}

        self.sk = SigningKey.generate(curve=NIST256p)
        self.vk = self.sk.verifying_key

        # connects to coordinator to get nodes and handle debugging
        debugsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        debugsocket.connect((self.server_ip, self.server_port))

        # keep debug socket alive
        debugsocket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        debugsocket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        debugsocket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 10 * 60)
        debugsocket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 5 * 60)
        debugsocket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 10)

        self.debugsocket = debugsocket

        self.print_debug("init")

        self.ballot = 0
        self.value_to_propagate = None # may be updated by a prepared(b, v) message or by controller()
        self.leader = None
    
        self.listening_thread = threading.Thread(target=self.listen)
        self.stop_listen = False
        self.controller_thread = threading.Thread(target=self.controller)

        self.listen_log = [] # rotating log, updated by listen() and used by propagate
        self.listen_log_lock = threading.Lock()

    def print_debug(self, msg):
        msg = DebugInfo(self.vk, msg)
        msg.send_with_tcp(self.debugsocket)

    def listen(self):
        
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind((self.host, self.port))

        self.listen_socket = s

        while not self.stop_listen:
            msg = Message.recv_with_udp(s)
            self.print_debug("rcv node msg " + str(msg.to_json()))
            if msg.TYPE == "prepare":
                if msg.ballot
                pass
            elif msg.TYPE == "propose":
                pass
            elif msg.TYPE == "accept":
                pass
            # the remaining need only to modify listen_log for the propagate_thread to use it
            else:
                self.listen_log_lock.acquire()
                if msg.TYPE == "proposed":
                    pass
                elif msg.TYPE == "prepared":
                    pass
                elif msg.TYPE == "accepted":
                    pass
                self.listen_log_lock.release()

        s.close()

    def controller(self): # TO DO
        while True:
            msg = MessageNoSignature.recv_with_tcp(self.debugsocket)
            if msg is None:
                break
            self.print_debug("rcv debug msg" + str(msg.to_json()))
            if msg.TYPE == "peerinfo":
                if msg.vk not in self.nodes:
                    self.nodes[msg.vk] = {"ip": msg.ip, "port": msg.port, "status":None}
                    self.print_debug("Got peer" + str(self.nodes[msg.vk]))
            elif msg.TYPE == "propagate":
                if self.propagate_thread is not None:
                    self.stop_propagate = True # flag that tells propagate_thread to stop trying to propagate
                    self.propagate_thread.join()
                self.propagate_thread = threading.Thread(target=self.propagate, args=(msg.value,))
                self.propagate_thread.start()
            elif msg.TYPE == "exit":
                break

    def propagate(self, value):
        # called by controller, uses listen_log to see which messages where received back
        self.stop_propagate = False
        self.ballot += 1
        self.print_debug("Will propagate " + value + " using ballot " + str(ballot))
        return   
        
    def start(self):

        if self.nodes is None:
            # receives other nodes' informations from coordinator
            myinfo = PeerInfo(self.vk, self.host, self.port)
            myinfo.send_with_tcp(self.debugsocket)
            
            msg = MessageNoSignature.recv_with_tcp(self.debugsocket)

            self.nodes = {}
            while msg is not None and msg.TYPE == "peerinfo":
                if msg.vk == myinfo.vk: # flag that we already got all peers
                    break
                self.nodes[msg.vk] = {"ip": msg.ip, "port": msg.port, "status":None}
                self.print_debug("Got peer" + str(self.nodes[msg.vk]))
                msg = MessageNoSignature.recv_with_tcp(self.debugsocket)
                # TO DO: use key exchange for an ephemeral key with this peer


        self.listening_thread.start()
        self.controller_thread.start()        

    def stop(self):
        self.stop_propagate = True
        self.propagate_thread.join()

        self.listening_thread.join() # kill these ??
        self.controller_thread.join()

    


    ########################################### OLD STUFF BELOW ###################################



    def prepare(self, ballot):
        self.ballot = ballot
        prepare_message = PrepareMessage(ballot)
        message = Message(prepare_message)
        self.broadcast(message)

    def propose(self, value):
        propose_message = ProposeMessage(self.ballot, value)
        message = Message(propose_message)
        self.broadcast(message)

    def learner(self):
        pass

    def broadcast(self, m):
        server = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

        # Enable port reusage so we will be able to run multiple clients and servers on single (host, port).
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

        # Enable broadcasting mode
        server.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        # Set a timeout so the socket does not block
        # indefinitely when trying to receive data.
        server.settimeout(0.2)
        message = b"your very important message"
        server.sendto(message, ('<broadcast>', 37020))
        print("message sent!")

    def acceptor(self):
        client = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)  # UDP

        # Enable port reusage so we will be able to run multiple clients and servers on single (host, port).
        client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

        # Enable broadcasting mode
        client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        client.bind((self.host, self.port))
        while True:
            message, addr = client.recvfrom(1024)
            print("received message: %s" % message)
            if PrepareMessage.is_valid(message):
                self.prepare_handler(message)
            elif ProposeMessage.is_valid(message):
                self.propose_handler(message)
            else:
                print('invalid message')
                pass

    def prepare_handler(self, message):
        prepare_message = PrepareMessage.from_string(message)
        if prepare_message.ballot > self.max_ballot:
            prepared_messages = [m.to_json() for m in self.proposed_messages]
            m = json.dump(prepared_messages)
            self.broadcast(m)
            # destination? signature?

    def propose_handler(self, message):
        propose_message = ProposeMessage.from_string(message)
