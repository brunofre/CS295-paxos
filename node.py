#!/usr/bin/env python3
import json
from attack import Attack
import socket
import random
import time
import socketserver
import time
import threading
import base64
import sys

from ecdsa.curves import NIST256p
from messages import *
from ecdsa import SigningKey


class Node:
    def __init__(self, host, port, coordinator_ip, coordinator_port, nodes=None, listen_handler_attack=None):
        self.host, self.port = host, port
        self.coordinator_ip, self.coordinator_port = coordinator_ip, coordinator_port
        self.nodes = nodes  # dict vk -> {ip, port, status}
        self.listen_handler_attack = listen_handler_attack

        self.sk = SigningKey.generate(curve=NIST256p)
        self.vk = vk_to_str(self.sk.verifying_key)

        # connects to coordinator to get nodes and handle debugging
        debug_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        debug_socket.connect((self.coordinator_ip, self.coordinator_port))

        # keep debug socket alive
        debug_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        debug_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        if not sys.platform.startswith('darwin'):
            debug_socket.setsockopt(
                socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 10 * 60)
        debug_socket.setsockopt(
            socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 5 * 60)
        debug_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 10)

        self.debug_socket = debug_socket

        self.print_debug("init")

        self.ballot = 0

        # values commited, note current position is len of this
        self.commited_values = []

        self.prepared_value = None  # contains the prepared value, if any

        self.propagate_thread = None

        self.listening_thread = threading.Thread(target=self.listening_handler)
        self.stop_listen = False
        self.coordinator_thread = threading.Thread(
            target=self.coordinator_handler)

        self.listen_log = []  # rotating log, updated by listen() and used by propagate
        self.listen_log_lock = threading.Lock()

    def print_debug(self, msg):
        msg = DebugInfo(self.vk, msg)
        msg.send(self.debug_socket)

    def listening_handler(self):

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind((self.host, self.port))

        self.listen_socket = s

        while not self.stop_listen:
            msg = Message.receive(s)
            self.print_debug("rcv node msg " + str(msg.to_json()))

            if msg.pos < len(self.commited_values):
                self.print_debug("msg for smaller position, dropping it")
            elif msg.pos > len(self.commited_values):
                self.print_debug(
                    f"msg for future position, (TO DO) asking {msg.vk} for its commited_values")
                # TO DO: get commited values from msg.vk
            elif msg.TYPE == CommitMessage.TYPE:
                self.stop_propagate = True
                self.print_debug(
                    f"Rcv commit value {msg.value} to pos {msg.pos}")
                self.commited_values.append(msg.value)
                self.prepared_value = None
            elif msg.TYPE != PreparedMessage.TYPE and msg.ballot < self.ballot:
                # note prepared msg can have lower ballot
                self.print_debug(
                    f"older ballot, we are at {self.ballot}, ignoring it")
                # to do: send Nack so nodes stop bothering us with lower ballot stuff?
            else:
                fromnode = self.nodes[msg.vk]
                if msg.TYPE == PrepareMessage.TYPE:
                    self.stop_propagate = True
                    self.leader = msg.vk
                    fromnode = self.nodes[msg.vk]
                    if self.listen_handler_attack is None:
                        preparedmsg = PreparedMessage(
                            msg.pos, self.ballot, self.prepared_value)
                        preparedmsg.send(
                            self.sk, fromnode["ip"], fromnode["port"])
                        self.ballot = msg.ballot
                    elif self.listen_handler_attack == Attack.AVILABILITY:
                        prepare_msg = PrepareMessage(msg.pos, msg.ballot + 1)
                        for k in self.nodes.keys():
                            target = self.nodes[k]
                            prepare_msg.send(
                                self.sk, target["ip"], target["port"])
                elif msg.TYPE == ProposeMessage.TYPE:
                    if self.leader == msg.vk:
                        self.stop_propagate = True
                        self.prepared_value = msg.value
                        accept_msg = AcceptMessage(msg.pos, msg.ballot)
                        accept_msg.send(
                            self.sk, fromnode["ip"], fromnode["port"])
                        self.ballot = msg.ballot
                # prepared/accept need only to modify listen_log for the propagate_thread to use it
                else:
                    self.listen_log_lock.acquire()
                    if msg.TYPE == PreparedMessage.TYPE or msg.TYPE == AcceptMessage.TYPE:
                        if self.propagate_thread is not None:  # otherwise we are not propagating, ignore it
                            self.listen_log.append(msg)
                    self.listen_log_lock.release()

        s.close()

    def coordinator_handler(self):
        while True:
            msg = CoordinatorMessage.receive(self.debug_socket)
            if msg is None:
                break
            self.print_debug("rcv debug msg" + str(msg.to_json()))
            time.sleep(1)
            if msg.TYPE == PeerInfo.TYPE:
                if msg.vk not in self.nodes:
                    self.nodes[msg.vk] = {"ip": msg.ip,
                                          "port": msg.port, "status": None}
                    self.print_debug("Got peer" + str(self.nodes[msg.vk]))
            elif msg.TYPE == CoordinatorPropagateMessage.TYPE:
                if msg.pos < len(self.commited_values):
                    self.print_debug(
                        f"recv propagate command for older pos ({msg.pos} vs {len(self.commited_values)}), ignoring it")
                    continue
                elif msg.pos > len(self.commited_values):
                    self.print_debug(
                        f"recv propagate command for future pos ({msg.pos} vs {len(self.commited_values)}), ignoring it")
                    continue  # TO DO: ask other peers for their commited_values so as to get to msg.pos
                if self.propagate_thread is not None:
                    self.print_debug("Stopping prev propagate thread")
                    # flag that tells propagate_thread to stop trying to propagate
                    self.stop_propagate = True
                    self.propagate_thread.join()
                self.propagate_thread = threading.Thread(
                    target=self.propagate, args=(msg.value, msg.attack))
                self.propagate_thread.start()
            elif msg.TYPE == CoordinatorExitCommand.TYPE:
                break
            elif msg.TYPE == "done":
                break
        self.debug_socket.close()

    def propagate(self, value, attack=None):

        pos = len(self.commited_values)

        if self.prepared_value is not None:
            value = self.prepared_value

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

        self.print_debug("Starting propagate of " + value +
                         " using ballot " + str(ballot))

        while not self.stop_propagate:

            # if propagate fails (i.e. no majority) we restart with original value
            value = original_value
            keys = random.sample(self.nodes.keys(), len(
                self.nodes))  # randomize key order
            prepared_keys = []  # peers that returned prepared msg
            prepared_ballot = 0  # highest ballot from a prepared msg recv
            accept_keys = []    # peers that accepted our propose()

            prepare_msg = PrepareMessage(pos, ballot)
            for k in keys:
                target = self.nodes[k]
                prepare_msg.send(self.sk, target["ip"], target["port"])
            # TO DO: better method here?? we just hope it works in 1sec
            time.sleep(1)
            self.listen_log_lock.acquire()
            for msg in self.listen_log:
                if msg.pos != pos:
                    continue
                if msg.TYPE == PreparedMessage.TYPE:
                    if msg.value is not None and msg.ballot > prepared_ballot:
                        value = msg.value  # we need the value with highest ballot
                        prepared_ballot = msg.ballot
                    prepared_keys.append(msg.vk)
            self.listen_log = []
            self.listen_log_lock.release()  # free it to get the accepts below back
            if self.stop_propagate:
                break
            elif len(prepared_keys) + 1 > (len(self.nodes)+1)/2:
                # we got majority, lets try to propose the value
                self.print_debug("Prepared succesful, value is " + str(value))

                if attack is None:
                    propose_msg = ProposeMessage(pos, ballot, value)
                    for k in prepared_keys:
                        target = self.nodes[k]
                        propose_msg.send(
                            self.sk, target["ip"], target["port"])
                    # TO DO: better method here?? we just hope it works in 1sec
                elif attack == Attack.CONSISTENCY:
                    propose_msg_a = ProposeMessage(pos, ballot, value)
                    propose_msg_b = ProposeMessage(
                        pos, ballot, str(int(value) + 100))
                    for i, k in enumerate(prepared_keys):
                        target = self.nodes[k]
                        if (i < len(prepared_keys) // 2):
                            propose_msg_a.send(
                                self.sk, target["ip"], target["port"])
                        else:
                            propose_msg_b.send(
                                self.sk, target["ip"], target["port"])

                time.sleep(1)
                self.listen_log_lock.acquire()
                for msg in self.listen_log:
                    if msg.TYPE == AcceptMessage.TYPE and msg.ballot == ballot and msg.pos == pos:
                        accept_keys.append(msg.vk)
                self.listen_log = []
                self.listen_log_lock.release()
                if len(accept_keys) + 1 > (len(self.nodes)+1)/2:
                    self.print_debug(
                        f"Succesfully propagated value {value} at position {pos}")
                    self.commited_values.append(value)
                    commitmsg = CommitMessage(pos, value)
                    for node in self.nodes.values():
                        commitmsg.send(self.sk, node['ip'], node['port'])
                    self.prepared_value = None
                    return
                    # TO DO: should stop paxos here, make a PaxosDoneMessage type and send it to coordinator, that sends it to other nodes
                else:
                    self.print_debug(
                        "Didn't get enough accepts: " + str(len(accept_keys)) + ", trying again")
            else:
                self.print_debug("Prepare phase failed with only " +
                                 str(len(prepared_keys)) + " extra nodes, trying again")

    def start(self):

        if self.nodes is None:
            # receives other nodes' informations from coordinator
            myinfo = PeerInfo(self.vk, self.host, self.port)
            myinfo.send(self.debug_socket)

            msg = CoordinatorMessage.receive(self.debug_socket)

            self.nodes = {}
            while msg is not None and msg.TYPE == PeerInfo.TYPE:
                if msg.vk == myinfo.vk:  # flag that we already got all peers
                    break
                self.nodes[msg.vk] = {"ip": msg.ip,
                                      "port": msg.port, "status": None}
                self.print_debug("Got peer" + str(self.nodes[msg.vk]))
                msg = CoordinatorMessage.receive(self.debug_socket)
                # TO DO: use key exchange for an ephemeral key with this peer

        self.listening_thread.start()
        self.coordinator_thread.start()

    def stop(self):
        self.stop_propagate = True
        self.propagate_thread.join()

        self.listening_thread.join()  # kill these ??
        self.coordinator_thread.join()
