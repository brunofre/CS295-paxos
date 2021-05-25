#!/usr/bin/env python3
import json
import socket
import time
import socketserver
import time
import threading

from ecdsa.curves import NIST256p
from messages import ProposeMessage, PrepareMessage, PeerInfo
from ecdsa import SigningKey

from coordinator import encapsulate_peer, decapsulate_peer, tcp_recv_msg, tcp_send_msg


class Node:
    def __init__(self, host, port, server_ip, server_port):
        self.host, self.port = host, port
        self.nodes = {} # dict vk -> {ip, port, status}

        self.sk = SigningKey.generate(curve=NIST256p)
        self.vk = self.sk.verifying_key

        # receives other nodes' informations from coordinator
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((server_ip, server_port))

        msg = PeerInfo.from_json({'type':'peerinfo',
                                  'vk':self.vk.to_string().decode("utf-8"),
                                  'host': host,
                                  'port': port}).to_string()

        tcp_send_msg(s, msg)

        msg = tcp_recv_msg(s)

        while len(msg["data"] != 0):
            peer = PeerInfo.from_string(msg["data"]).to_json()
            self.nodes[peer['vk']] = {"ip": peer['ip'], "port": peer['port'], "status":None}
            msg = tcp_recv_msg(s)
            # TO DO: use key exchange for an ephemeral key with this peer

        s.close()

        self.ballot = 0
        self.value_to_propagate = None
        self.leader = None
        self.listening_thread = None # calls listen
        self.controller_thread = None 

        self.listen_log = [] # rotating log, modified by listen() and used by propagate_thread

    def listen(self):
        # listen creates propagate() thread on debug message "propagate this" recv from coordinator
        pass

    def controller(self):
        # for now, controlled by coordinator so we just open a debugging tcp connection to it and
        # wait for "propagate this" messages
        pass

    def start(self):
        self.listening_thread.start()
        self.controller_thread.start()        

    def stop(self):
        self.listening_thread.join()
        self.controller_thread.join()

    def propagate(self, value):
        pass



    ########################################### OLD STUFF BELOW ###################################



    def prepare(self, ballot_number):
        self.ballot_number = ballot_number
        prepare_message = PrepareMessage(ballot_number)
        message = Message(prepare_message)
        self.broadcast(message)

    def propose(self, value):
        propose_message = ProposeMessage(self.ballot_number, value)
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
        if prepare_message.ballot_number > self.max_ballot_number:
            prepared_messages = [m.to_json() for m in self.proposed_messages]
            m = json.dump(prepared_messages)
            self.broadcast(m)
            # destination? signature?

    def propose_handler(self, message):
        propose_message = ProposeMessage.from_string(message)
