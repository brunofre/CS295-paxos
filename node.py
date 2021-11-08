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

from collections import defaultdict

from ecdsa.curves import NIST256p
from messages import *
from ecdsa import SigningKey

SLOW = False

class Node:
    def __init__(self, host, port, coordinator_ip, coordinator_port, nodes=None, attack=None, middleware=False):
        """ a node is made of three threads: 
                listening = listens for incoming messages from other nodes
                debug = interacts with coordinator, getting peer infos and debug msgs
                propagate = responsible for propagating new values that this node is proposing, using messages from listening_t above 
                
            parameters:
            host = host for listening_thread
            port = port for listening_thread
            coord_ip/port = address to connect to for debug_thread
            nodes = optional explicit info of other nodes instead of using debug_thread,
                    given as a verifying_key : {ip, port, status} dict
            attack = make this a malicious node, using this attack type
            middleware = enable middleware defense mechanisms
        """
        self.host, self.port = host, port
        self.coordinator_ip, self.coordinator_port = coordinator_ip, coordinator_port
        self.nodes = nodes  # dict vk -> {ip, port, status}
        self.attack = attack # 

        self.sk = SigningKey.generate(curve=NIST256p)
        self.vk = key_to_str(self.sk.verifying_key)

        self.ballot = 0 # highest seen

        # thread that handles node info acquisition and debug msgs
        self.debug_thread = threading.Thread(target=self.coordinator_handler)

        # we are doing commits to a log, so values are added to a list and pos
        # is given implicitly
        self.commited_values = []

        # contains the prepared value for current pos, if any
        # i.e. this is the value of the highest proposed ballot that we Accepted
        self.prepared_value = None  

        # handles propagation independently of incoming message listening thread
        # note we use is_alive as a means to test if we are propagating
        self.propagate_thread = threading.Thread()

        # handles incoming messages, updating log below
        self.listening_thread = threading.Thread(target=self.listening_handler)
        self.stop_listen = False
        
        # rotating log for messages received, updated by listen() and used by propagate
        self.listen_log = []  
        self.listen_log_lock = threading.Lock()

        # middleware data to handle (some) attacks
        self.middleware_proposes = {}
        self.middleware_prepares = defaultdict(int)
        self.middleware_enabled = middleware

    def print_debug(self, msg):
        msg = DebugInfo(self.vk, msg)
        msg.send(self.debug_socket)

    def listening_handler(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind((self.host, self.port))

        while not self.stop_listen:
            msg = Message.receive(s)
            self.print_debug(f"rcv node {msg.vk[:5]} msg {msg.to_json()}")
            from_node = self.nodes[msg.vk]

            if msg.pos < len(self.commited_values):
                self.print_debug("msg for smaller position, dropping it")
            elif msg.pos > len(self.commited_values):
                self.print_debug("msg for future position, dropping it")
                # TO DO: get commited values from msg.vk
            elif self.middleware_enabled and from_node['status'] == 'malicious':
                # the sending node has been detected as malicious by this node, drop message
                continue
            elif msg.TYPE == MiddlewareProposeRecv.TYPE:
                if self.middleware_enabled:
                    index = (msg.vk, msg.pos, msg.ballot)
                    if index not in self.middleware_proposes:
                        self.middleware_proposes[index] = msg.value
                    elif self.middelware_proposes[index] != msg.value:
                        self.nodes[msg.tovk]['status'] = 'malicious'
            #####
            elif msg.TYPE == CommitMessage.TYPE:
                # we trust that nodes will never send Commit maliciously (alternatively we could only allow
                # such msgs from trusted nodes or use the coordinator).
                self.stop_propagate = True
                self.propagate_thread.join()
                self.print_debug(f"rcv commit value {msg.value} to pos {msg.pos}")
                self.commited_values.append(msg.value)
                self.prepared_value = None
            elif msg.TYPE != PreparedMessage.TYPE and msg.ballot < self.ballot:
                # note prepared is the only that can have a lower ballot
                self.print_debug(f"older ballot, we are at {self.ballot}, ignoring it")
                # TO DO: send Nack so nodes stop bothering us with lower ballot stuff
            else:
                # note that here msg.ballot is appropriate for this message
                if msg.TYPE == PrepareMessage.TYPE:
                    if self.middleware_enabled:
                        # Protection against ballot climbing attacks:
                        #   if a node tried to prepare 'too much' for this exact position,
                        #   then we assume it is malicious 
                        # Currently we simply count the number of such messages, but in
                        #   production one would use something more forgiving/sophisticated
                        #   say by allowing x prepares per pos per node per time slot
                        key = (msg.vk, msg.pos)
                        self.middleware_prepares[key] += 1
                        if self.middleware_prepares[key] >= 3:
                            from_node['status'] = 'malicious'
                            continue
                    if self.propagate_thread.is_alive():
                        self.print_debug("Got higher ballot prepare, stopping propagate thread")
                        self.stop_propagate = True
                        self.propagate_thread.join()
                    self.leader = msg.vk
                    if self.attack == Attack.LIVENESS:
                        # Ballot climbing attack
                        prepare_msg = PrepareMessage(msg.pos, msg.ballot + 1)
                        for target in self.nodes.values():
                            prepare_msg.send(self.sk, target["ip"], target["port"])
                    else:
                        prepared_msg = PreparedMessage(msg.pos, self.ballot, self.prepared_value)
                        prepared_msg.send(self.sk, from_node["ip"], from_node["port"])
                        self.ballot = msg.ballot
                elif msg.TYPE == ProposeMessage.TYPE:
                    if self.middleware_enabled:
                        # Security defense: we help other nodes by letting them know
                        #   what this node is trying to propose for this pos
                        #   if it doesnt match the value they propose to target,
                        #   target should assume this node is malicious by def. of Paxos
                        prop_recv = MiddlewareProposeRecv(msg.pos, msg.value, msg.ballot, msg.vk)
                        for target in self.nodes.values():
                            prop_recv.send(self.sk, target['ip'], target['port'])
                    # We need only consider proposes from current leader, otherwise drop
                    #   obs: msg.vk is probably malicious, but dropping is good enough
                    if self.leader != msg.vk:
                        continue
                    # remember, this is a higher propose, we should stop propagating our lower one
                    if self.propagate_thread.is_alive():
                        self.stop_propagate = True
                        self.propagate_thread.join()
                    if self.middleware_enabled and\
                            ((msg.vk, msg.pos, msg.ballot) in self.middleware_proposes and
                                msg.value != self.middleware_proposes[(msg.vk, msg.pos, msg.ballot)]) or\
                            ((self.prepared_value is not None) and self.prepared_value != msg.value):
                        # This is the counterpart to the above: if some other node warned us of a different 
                        # value proposed by this party, then we know this node is malicious
                        self.print_debug("Detected attack on Paxos security")
                        from_node['status'] = 'malicious'
                        continue
                    self.prepared_value = msg.value
                    accept_msg = AcceptMessage(msg.pos, msg.ballot)
                    accept_msg.send(self.sk, from_node["ip"], from_node["port"])
                    self.ballot = msg.ballot
                # This is a prepared/accept message, we only need to modify listen_log 
                # so that propagate_thread can use it
                else:
                    assert msg.TYPE == PreparedMessage.TYPE or msg.TYPE == AcceptMessage.TYPE
                    if self.propagate_thread is None:
                        # something funny happened, just drop
                        continue
                    self.listen_log_lock.acquire()
                    self.listen_log.append(msg)
                    self.listen_log_lock.release()

        s.close()


    def coordinator_handler(self):

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

        self.print_debug("Initialized")

        while True:
            msg = CoordinatorMessage.receive(self.debug_socket)
            if msg is None:
                break
            self.print_debug("rcv debug msg" + str(msg.to_json()))
            if SLOW: time.sleep(1)
            if msg.TYPE == PeerInfo.TYPE:
                if msg.vk not in self.nodes and msg.vk != self.vk:
                    self.nodes[msg.vk] = {"ip": msg.ip,
                                          "port": msg.port, "status": None}
                    self.print_debug(f"Got peer {self.nodes[msg.vk]}")
            elif msg.TYPE == CoordinatorPropagateMessage.TYPE:
                if msg.pos < len(self.commited_values):
                    self.print_debug(f"recv propagate command for older pos ({msg.pos} vs {len(self.commited_values)}), ignoring it")
                    continue
                elif msg.pos > len(self.commited_values):
                    self.print_debug(f"recv propagate command for future pos ({msg.pos} vs {len(self.commited_values)}), ignoring it")
                    continue  # TO DO: ask other peers for their commited_values so as to get to msg.pos
                if self.propagate_thread is not None:
                    self.print_debug("Stopping prev propagate thread since we got a new request")
                    self.stop_propagate = True
                    self.propagate_thread.join()
                self.propagate_thread = threading.Thread(target=self.propagate, args=(msg.value,))
                self.propagate_thread.start()
            elif msg.TYPE == CoordinatorExitCommand.TYPE:
                self.stop()
                self.debug_socket.close()
                return
            else
                assert 1 == 2


    def propagate(self, value):

        pos = len(self.commited_values)

        if self.attack != Attack.IGNORE_PREPARED and self.prepared_value is not None:
            value = self.prepared_value

        self.stop_propagate = False
        self.leader = self.vk

        # clean up so we don't take older messages as acceptances
        if SLOW: time.sleep(1)
        self.listen_log_lock.acquire()
        listen_log = []
        self.listen_log_lock.release()

        original_value = value

        # this is the timeout for waiting for prepared/accept messages
        # we increase it by delta seconds each time we fail
        # note this is reset each time we start propagating
        delta_between_tries = 0.5
        time_wait_for_messages = 0.5 - delta_between_tries
        
        while not self.stop_propagate:

            time_wait_for_messages += delta_between_tries
            if SLOW: time.sleep(2)
            self.ballot += 1
            ballot = self.ballot

            self.print_debug(f"Starting propagate of {value} using ballot {ballot}")

            # if propagate fails (i.e. no majority) we restart with original value
            value = original_value
            random.seed()
            keys = random.sample([k for k in self.nodes.keys() if self.nodes[k]['status'] != 'malicious'],
                 len(self.nodes))  # randomize key order
            prepared_keys = []  # peers that returned prepared msg
            prepared_ballot = -1  # highest ballot from a prepared msg recv
            accept_keys = []    # peers that accepted our propose()

            prepare_msg = PrepareMessage(pos, ballot)
            for k in keys:
                target = self.nodes[k]
                prepare_msg.send(self.sk, target["ip"], target["port"])
            time.sleep(time_wait_for_messages)

            self.listen_log_lock.acquire()
            for msg in self.listen_log:
                if msg.pos != pos or msg.TYPE != PreparedMessage.TYPE:
                    continue
                if self.attack != Attack.IGNORE_PREPARED and msg.value is not None and msg.ballot > prepared_ballot:
                    value = msg.value  # we need the value with highest ballot
                    prepared_ballot = msg.ballot
                prepared_keys.append(msg.vk)
            self.listen_log = []
            self.listen_log_lock.release()

            if self.stop_propagate:
                break

            # we got majority, lets try to propose the value
            if len(prepared_keys) + 1 > (len(self.nodes)+1)/2: 
                self.print_debug(f"Prepared succesful, value is {value}")

                if self.attack == Attack.SAFETY:
                    value = str(value)
                    propose_msg_a = ProposeMessage(pos, ballot, value)
                    propose_msg_b = ProposeMessage(pos, ballot, value + " safety attack")
                    for i, k in enumerate(prepared_keys):
                        target = self.nodes[k]
                        m = propose_msg_a if i < len(prepared_keys) // 2 else propose_msg_b
                        m.send(self.sk, target["ip"], target["port"])
                else:
                    if self.attack == Attack.IGNORE_PREPARED:
                        value = f"{value} ignored prepared msgs" # just for debugging purposes
                    propose_msg = ProposeMessage(pos, ballot, value)
                    for k in prepared_keys:
                        target = self.nodes[k]
                        propose_msg.send(self.sk, target["ip"], target["port"])

                time.sleep(time_wait_for_messages)
                self.listen_log_lock.acquire()
                for msg in self.listen_log:
                    if msg.TYPE == AcceptMessage.TYPE and msg.ballot == ballot and msg.pos == pos:
                        accept_keys.append(msg.vk)
                self.listen_log = []
                self.listen_log_lock.release()
                if len(accept_keys) + 1 > (len(self.nodes)+1)/2:
                    self.print_debug(f"Succesfully propagated value {value} at position {pos}, will now commit")
                    self.commited_values.append(value)
                    if self.attack == Attack.SAFETY:
                        for vk, node in self.nodes.items():
                            if vk in prepared_keys and prepared_keys.index(vk) >= len(prepared_keys) // 2:
                                # note we choose to send value to all remaining nodes,
                                # even if we didnt really receive back Prepared
                                commit_msg = CommitMessage(pos, value + " safety attack")
                            else:
                                commit_msg = CommitMessage(pos, value)
                            commit_msg.send(self.sk, node['ip'], node['port'])
                    else:
                        commit_msg = CommitMessage(pos, value)
                        for node in self.nodes.values():
                            commit_msg.send(self.sk, node['ip'], node['port'])
                    self.prepared_value = None
                    return
                else:
                    self.print_debug(f"Didn't get enough Accepts: {len(accept_keys)}, trying again")
            else:
                self.print_debug(f"Prepare phase failed with only {len(prepared_keys)} prepared msgs, trying again")

    def start(self):

        self.debug_thread.start()

        # tell coordinator we exist
        PeerInfo(self.vk, self.host, self.port, self.attack).send(self.debug_socket)

        if self.nodes is None:
            self.nodes = {}
            # receives other nodes' informations from coordinator
            msg = CoordinatorMessage.receive(self.debug_socket)

            while msg is not None and msg.TYPE == PeerInfo.TYPE:
                if msg.vk == self.vk:  # flag that we already got all peers
                    break
                self.nodes[msg.vk] = {"ip": msg.ip,
                                      "port": msg.port, "status": None}
                self.print_debug(f"Got peer{self.nodes[msg.vk]}")
                msg = CoordinatorMessage.receive(self.debug_socket)
                # TO DO: use key exchange for an ephemeral key with this peer

        self.listening_thread.start()

    def stop(self):
        self.stop_propagate = True
        self.stop_listen = True
        if self.propagate_thread.is_alive():
            self.propagate_thread.join()
        self.listening_thread.join() 
