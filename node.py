#!/usr/bin/env python3
import json
import socket
import random
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
        self.vk = vk_to_str(self.sk.verifying_key)

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
        self.prepared_value = None # contains the prepared value, if any

        #self.value_to_propagate = None # may be updated by controller()
    
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

            if msg.TYPE != "prepared" and msg.ballot < self.ballot:
                # node prepared msg can have lower ballot
                self.print_debug("older ballot, we are at " + str(self.ballot))
                # to do: send Nack so nodes stop bothering us with lower ballot stuff?
            else:
                fromnode = self.nodes[msg.vk]
                if msg.TYPE == "prepare":
                    self.stop_propagate = True
                    self.leader = msg.vk
                    fromnode = self.nodes[msg.vk]
                    preparedmsg = PreparedMessage(self.ballot, self.prepared_value)
                    preparedmsg.send_with_udp(fromnode["ip"], fromnode["port"])
                    self.ballot = msg.ballot
                elif msg.TYPE == "propose":
                    if self.leader == msg.vk:
                        self.stop_propagate = True
                        self.prepared_value = msg.value
                        acceptmsg = AcceptMessage(msg.ballot)
                        acceptmsg.send_with_udp(fromnode["ip"], fromnode["port"])
                        self.ballot = msg.ballot
                # prepared/accept need only to modify listen_log for the propagate_thread to use it
                else:
                    self.listen_log_lock.acquire()
                    if msg.TYPE == "prepared" or msg.TYPE == "accept":
                        if self.propagate_thread is not None: # otherwise we are not propagating, ignore it
                            self.listen_log.append(msg)
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
            elif msg.TYPE == "done":
                break

    def propagate(self, value):

        self.stop_propagate = False
        self.leader = self.vk

        self.ballot += 1
        ballot = self.ballot

        # clean up so we don't take older messages as acceptances
        time.sleep(1)
        self.listen_log_lock.acquire()
        listen_log = []
        self.listen_log_lock.release()

        original_value = value 

        self.print_debug("Starting propagate of " + value + " using ballot " + str(ballot))

        while not self.stop_propagate:    

            value = original_value # if propagate fails (i.e. no majority) we restart with original value
            keys = random.sample(self.nodes.keys(), len(self.nodes)) # randomize key order
            prepared_keys = []  # peers that returned prepared msg
            prepared_ballot = 0 # highest ballot from a prepared msg recv
            accept_keys = []    # peers that accepted our propose()

            preparemsg = PrepareMessage(ballot)
            for k in keys:
                target = self.nodes[k]
                preparemsg.send_with_udp(target["ip"], target["port"])
            time.sleep(1) # TO DO: better method here?? we just hope it works in 1sec
            self.listen_log_lock.acquire()
            for msg in self.listen_log:
                if msg.TYPE == "prepared":
                    if msg.value is not None and msg.ballot > prepared_ballot:
                        value = msg.value # we need the value with highest ballot
                        prepared_ballot = msg.ballot
                    prepared_keys.append(msg.vk)
            self.listen_log = []
            self.listen_log_lock.release() # free it to get the accepts below back
            if self.stop_propagate:
                break
            elif len(prepared_keys) + 1 > (len(self.nodes)+1)/2:
                # we got majority, lets try to propose the value
                self.print_debug("Prepared succesful, value is " + str(value))
                proposemsg = ProposeMessage(ballot, value)
                for k in prepared_keys:
                    target = self.nodes[k]
                    proposemsg.send_with_udp(target["ip"], target["port"])
                time.sleep(1) # TO DO: better method here?? we just hope it works in 1sec
                self.listen_log_lock.acquire()
                for  msg in self.listen_log:
                    if msg.TYPE == "accept" and msg.ballot == ballot:
                        accept_keys.append(msg.vk)
                self.listen_log = []
                self.listen_log_lock.release()
                if len(accept_keys) + 1 > (len(self.nodes)+1)/2:
                    self.print_debug("Succesfully propagated value " + str(value))
                    # TO DO: should stop paxos here, make a PaxosDoneMessage type and send it to coordinator, that sends it to other nodes
                else:
                    self.print_debug("Didn't get enough accepts: " + str(len(accept_keys)) + ", trying again")
            else:
                self.print_debug("Prepare phase failed with only " + str(len(prepared_keys)) + " extra nodes, trying again")
        
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
