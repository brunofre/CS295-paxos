from attack import Attack
import json
import socket
import struct
from ecdsa.curves import NIST256p
from ecdsa.keys import SigningKey, VerifyingKey

# HELPERS


def tcp_send_msg(sock, msg):
    if isinstance(msg, str):
        msg = msg.encode()
    msg = struct.pack('>I', len(msg)) + msg
    return sock.sendall(msg)


def tcp_recv_msg(sock):
    raw_msglen = sock.recv(4)
    if raw_msglen is None or len(raw_msglen) < 4:
        return None
    msglen = struct.unpack('>I', raw_msglen)[0]
    r = sock.recvfrom(msglen)
    if len(r[0]) != msglen:
        return None
    return {"data": r[0].decode(), "from": r[1]}


def udp_send_msg(ip, port, msg):
    if isinstance(msg, str):
        msg = msg.encode()
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.sendto(msg, (ip, port))
    s.close()


def udp_recv_msg(sock):
    r = sock.recv(4096)
    return r.decode()


def key_to_str(key):
    if not isinstance(key, str):
        key = key.to_string().hex()
    return key


def str_to_vk(st):
    return VerifyingKey.from_string(bytes.fromhex(st), curve=NIST256p)


def str_to_sk(st):
    return SigningKey.from_string(bytes.fromhex(st), curve=NIST256p)

################

# XMessage classes only need to implement init, to_json, from_json and inherit Message


class Message:

    TYPE = None
    vk = None

    def __init__(self):
        pass

    @classmethod
    def is_valid(cls, message):
        j = json.loads(message)
        return j['type'] == cls.TYPE

    @staticmethod
    def msg_handler(message):
        j = json.loads(message)
        payload_string = j['payload_string']
        signature = bytes.fromhex(j['signature'])
        vk = j['vk']

        assert str_to_vk(vk).verify(signature, payload_string.encode())
        payload = json.loads(payload_string)

        TYPES = {PrepareMessage, PreparedMessage,
                 ProposeMessage, AcceptMessage, CommitMessage}

        for msgtype in TYPES:
            if msgtype.is_valid(payload_string):
                msg = msgtype.from_json(payload)

        assert msg is not None
        msg.vk = vk
        return msg

    @classmethod
    def from_string(cls, message):
        if isinstance(message, bytes):
            message = message.decode()
        return cls.msg_handler(message)

    def to_string(self, sk):
        payload_string = json.dumps(self.to_json())
        signature = sk.sign(payload_string.encode()).hex()
        j = {
            'payload_string': payload_string,
            'signature': signature,
            'vk': key_to_str(sk.verifying_key)
        }
        return json.dumps(j)

    def send(self, sk, target_ip, target_port):
        msg = self.to_string(sk)
        udp_send_msg(target_ip, target_port, msg)

    @classmethod
    def receive(cls, sock):
        msg = udp_recv_msg(sock)
        if msg is None:
            return None
        return cls.msg_handler(msg)


class CoordinatorMessage:

    TYPE = None

    @classmethod
    def is_valid(cls, message):
        j = json.loads(message)
        return j['type'] == cls.TYPE

    def to_string(self):
        return json.dumps(self.to_json())

    @staticmethod
    def msg_handler(msg):
        if isinstance(msg, bytes):
            msg = msg.decode()
        TYPES = {PeerInfo, DebugInfo,
                 CoordinatorExitCommand, CoordinatorPropagateMessage}
        for msgtype in TYPES:
            if msgtype.is_valid(msg):
                j = json.loads(msg)
                return msgtype.from_json(j)
        return None

    @classmethod
    def from_string(cls, msg):
        return cls.msg_handler(msg)

    def send(self, sock):
        msg = self.to_string()
        tcp_send_msg(sock, msg)

    @classmethod
    def receive(cls, sock):
        msg = tcp_recv_msg(sock)
        if msg is None:
            return None
        return cls.msg_handler(msg["data"])


class PrepareMessage(Message):

    TYPE = 'prepare'

    def __init__(self, pos, ballot):
        self.pos, self.ballot = int(pos), ballot

    def to_json(self):
        return {
            'type': self.TYPE,
            'ballot': self.ballot,
            'pos': self.pos
        }

    @classmethod
    def from_json(cls, j):
        pos = j['pos']
        ballot = j['ballot']
        return cls(pos, ballot)


class PreparedMessage(Message):

    TYPE = 'prepared'

    def __init__(self, pos, ballot, value):
        self.pos, self.ballot = int(pos), ballot
        self.value = value

    def to_json(self):
        return {
            'type': self.TYPE,
            'pos': self.pos,
            'ballot': self.ballot,
            'value': self.value
        }

    @classmethod
    def from_json(cls, j):
        pos = j['pos']
        ballot = j['ballot']
        value = j['value']
        return cls(pos, ballot, value)


class ProposeMessage(Message):

    TYPE = 'propose'

    def __init__(self, pos, ballot, value):
        self.pos, self.ballot = int(pos), ballot
        self.value = value

    def to_json(self):
        return {
            'type': self.TYPE,
            'pos': self.pos,
            'ballot': self.ballot,
            'value': self.value
        }

    @classmethod
    def from_json(cls, j):
        pos = j['pos']
        ballot = j['ballot']
        value = j['value']
        return cls(pos, ballot, value)


class AcceptMessage(Message):

    TYPE = 'accept'

    def __init__(self, pos, ballot):
        self.pos, self.ballot = int(pos), ballot

    def to_json(self):
        return {
            'type': self.TYPE,
            'pos': self.pos,
            'ballot': self.ballot
        }

    @classmethod
    def from_json(cls, j):
        pos = j['pos']
        ballot = j['ballot']
        return cls(pos, ballot)


class CommitMessage(Message):

    TYPE = 'commit'

    def __init__(self, pos, value):
        self.pos, self.value = int(pos), value

    def to_json(self):
        return {
            'type': self.TYPE,
            'pos': self.pos,
            'value': self.value
        }

    @classmethod
    def from_json(cls, j):
        pos = j['pos']
        value = j['value']
        return cls(pos, value)


class PeerInfo(CoordinatorMessage):

    TYPE = 'peerinfo'

    def __init__(self, vk, sk, ip, port, attack=None):
        self.vk = key_to_str(vk)
        self.sk = key_to_str(sk)
        self.ip = ip
        self.port = port
        self.attack = attack

    def to_json(self):
        return {
            'type': self.TYPE,
            'vk': self.vk,
            'sk': self.sk,
            'ip': self.ip,
            'port': self.port,
            'attack': self.attack.value if self.attack is not None else None
        }

    @classmethod
    def from_json(cls, j):
        vk = j['vk']
        sk = j['sk']
        ip = j['ip']
        port = j['port']
        attack = Attack(j['attack']) if j['attack'] is not None else None
        return cls(vk, sk, ip, port, attack)


class DebugInfo(CoordinatorMessage):

    TYPE = 'debug'

    def __init__(self, vk, msg):
        self.msg = msg
        if not isinstance(vk, str):
            vk = key_to_str(vk)
        self.vk = vk

    def to_json(self):
        return {
            'type': self.TYPE,
            'vk': self.vk,  # we are using vk as an ID
            'msg': self.msg
        }

    @classmethod
    def from_json(cls, j):
        msg = j['msg']
        vk = j['vk']
        return cls(vk, msg)


class CoordinatorExitCommand(CoordinatorMessage):

    TYPE = 'exit'

    def __init__(self):
        pass

    def to_json(self):
        return {
            'type': self.TYPE,
        }

    @classmethod
    def from_json(cls, j):
        return cls()


class CoordinatorPropagateMessage(CoordinatorMessage):

    TYPE = 'propagate'

    def __init__(self, pos, value):
        self.pos, self.value = int(pos), value

    def to_json(self):
        return {
            'type': self.TYPE,
            'pos': self.pos,
            'value': self.value
        }

    @classmethod
    def from_json(cls, j):
        pos = j['pos']
        value = j['value']
        return cls(pos, value)
