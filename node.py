#!/usr/bin/env python3
import json
import socket
import time
import socketserver
import time
import threading
import base64

from ecdsa.curves import NIST256p
from messages import ProposeMessage, PrepareMessage, PeerInfo, ControllerPropagateMessage, ControllerExitCommand, vk_to_str, str_to_vk
from ecdsa import SigningKey

from coordinator import tcp_recv_msg, tcp_send_msg


class Node:
    def __init__(self, host, port, server_ip, server_port, nodes=None):
        self.host, self.port = host, port
        self.server_ip, self.server_port = server_ip, server_port
        self.nodes = {} # dict vk -> {ip, port, status}

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

        if nodes is None:
            # receives other nodes' informations from coordinato
            msg = PeerInfo.from_json({'type':'peerinfo',
                                    'vk':vk_to_str(self.vk),
                                    'ip': host,
                                    'port': port}).to_string()

            tcp_send_msg(debugsocket, msg)

            msg = tcp_recv_msg(debugsocket)

            while msg is not None:
                peer = PeerInfo.from_string(msg["data"]).to_json()
                self.nodes[peer['vk']] = {"ip": peer['ip'], "port": peer['port'], "status":None}
                msg = tcp_recv_msg(debugsocket)
                # TO DO: use key exchange for an ephemeral key with this peer

        self.debugsocket = debugsocket

        self.ballot = 0
        self.value_to_propagate = None # may be updated by a prepared(b, v) message or by controller()
        self.leader = None
    
        self.listening_thread = threading.Thread(target=self.listen)
        self.controller_thread = threading.Thread(target=self.controller)

        self.listen_log = [] # rotating log, updated by listen() and used by propagate

    def listen(self):
        # create UDP thread for listening, answer messages as in diagram and stores messages for propagate_thread
        pass

    def controller(self):
        # for now, controlled by coordinator so we just open a debugging tcp connection to it and
        # wait for "propagate this" messages
        debugsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        debugsocket.connect((self.server_ip, self.server_port))

        # keep debug socket alive
        debugsocket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        debugsocket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        debugsocket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 10 * 60)
        debugsocket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 5 * 60)
        debugsocket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 10)

        tcp_send_msg(debugsocket, "debug socket")    

        self.ds = debugsocket # will be used to send back debug logs to coordinator

        while True:
            msg = tcp_recv_msg(self.ds)
            if ControllerPropagateMessage.is_valid(msg):
                msg = ControllerPropagateMessage.from_string(msg).to_json()
                if self.propagate_thread is not None:
                    self.stop_propagate = True # flag that tells propagate_thread to stop trying to propagate
                    self.propagate_thread.join()
                self.propagate_thread = threading.Thread(target=self.propagate, args=(msg["value"]))
                self.propagate_thread.start()
            elif ControllerExitCommand.is_valid(msg):
                break
            else:
                break

    def propagate(self, value):
        # called by controller, uses listen_log to see which messages where received back
        self.ballot += 1
        pass    
        
    def start(self):
        self.listening_thread.start()
        self.controller_thread.start()        

    def stop(self):
        self.stop_propagate = True
        self.propagate_thread.join()

        self.listening_thread.join() # kill these ??
        self.controller_thread.join()

    


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
