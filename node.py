#!/usr/bin/env python3
import json
import socket
import time
import socketserver
import time
import threading

from ecdsa.curves import NIST256p
from messages import ProposeMessage, PrepareMessage
from ecdsa import SigningKey


class Node:
    def __init__(self, host, port, nodes):
        self.host, self.port = host, port
        self.nodes = nodes
        self.sk = SigningKey.generate(curve=NIST256p)
        self.vk = self.sk.verifying_key
        self.acceptor_thread = threading.Thread(target=self.acceptor)
        self.learner_thread = threading.Thread(target=self.learner)
        self.proposed_messages = []
        self.max_ballot_number = 0

    def start(self):
        self.acceptor_thread.start()
        self.learner_thread.start()

    def stop(self):
        self.acceptor_thread.join()
        self.learner_thread.join()

    def prepare(self, n):
        m = PrepareMessage(n)
        self.broadcast(m)

    def propose(self, n):
        ProposeMessage(n)
        self.broadcast(n)

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

    def verify_signature(self, message):
        pass
