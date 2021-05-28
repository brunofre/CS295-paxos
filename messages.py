import json
import socket
import struct
import base64
from ecdsa.curves import NIST256p

from ecdsa.keys import VerifyingKey


def tcp_send_msg(sock, msg):
    if isinstance(msg, str):
        msg = msg.encode("utf-8")
    msg = struct.pack('>I', len(msg)) + msg
    return sock.sendall(msg)


def tcp_recv_msg(sock):
    raw_msglen = sock.recv(4)
    if raw_msglen is None or len(raw_msglen) < 4:
        return None
    msglen = struct.unpack('>I', raw_msglen)[0]
    r = sock.recvfrom(msglen)
    assert len(r[0]) == msglen
    return {"data": r[0].decode("utf-8"), "from": r[1]}


def vk_to_str(vk):
    return vk.to_string()


def str_to_vk(st):
    return VerifyingKey.from_string(st, curve=NIST256p)

# XMessage classes only need to implement init, to_json, from_json and inherit Message


class Message:

    TYPE = None

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
        signature = j['signature']
        vk = str_to_vk(j['vk'])

        assert vk.verify(signature, payload_string)
        payload = json.loads(payload_string)

        TYPES = {PrepareMessage, PreparedMessage,
                 ProposeMessage, AcceptMessage}

        for msgtype in TYPES:
            if msgtype.is_valid(payload_string):
                return msgtype.from_json(payload)

    @classmethod
    def from_string(cls, message):
        if isinstance(message, bytes):
            message = message.decode("utf-8")
        return cls.msg_handler(message)

    def to_string(self, sk):
        payload_string = json.dumps(self.to_json())
        signature = sk.sign(payload_string)
        j = {
            'payload_string': payload_string,
            'signature': signature,
            'vk': sk.verifying_key
        }
        return json.dumps(j)

    def send_with_udp(self, target_ip, target_port):
        msg = self.to_string()
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.sendto(msg, (target_ip, target_port))
        s.close()


class MessageNoSignature:

    TYPE = None

    @classmethod
    def is_valid(cls, message):
        j = json.loads(message)
        return j['type'] == cls.TYPE

    def to_string(self):
        return json.dumps(self.to_json())

    def send_with_tcp(self, sock):
        msg = self.to_string()
        tcp_send_msg(sock, msg)

    @staticmethod
    def msg_handler(msg):
        if isinstance(msg, bytes):
            msg = msg.decode("utf-8")
        TYPES = {PeerInfo, DebugInfo, ControllerExitCommand}
        for msgtype in TYPES:
            if msgtype.is_valid(msg):
                j = json.loads(msg)
                return msgtype.from_json(j)

    @classmethod
    def from_string(cls, msg):
        return cls.msg_handler(msg)

    @classmethod
    def recv_with_tcp(cls, sock):
        msg = tcp_recv_msg(sock)
        if msg is None:
            return None
        return cls.msg_handler(msg["data"])


class PrepareMessage(Message):

    TYPE = 'prepare'

    def __init__(self, ballot_number):
        self.ballot_number = ballot_number

    def to_json(self):
        return {
            'type': self.TYPE,
            'ballot_number': self.ballot_number
        }

    @classmethod
    def from_json(cls, j):
        ballot_number = j['ballot_number']
        return cls(ballot_number)


class PreparedMessage(Message):

    TYPE = 'prepared'

    def __init__(self, propose_messages):
        self.propose_messages = propose_messages

    def to_json(self):
        return {
            'type': self.TYPE,
            'propose_messages': [propose_message.to_json() for propose_message in self.propose_messages]
        }

    # TO DO: fix this
    @classmethod
    def from_json(cls, j):
        propose_messages = [PrepareMessage().from_json(
            propose_message) for propose_message in j['propose_messages']]
        return cls(propose_messages)


class ProposeMessage(Message):

    TYPE = 'propose'

    def __init__(self, ballot_number, value):
        self.ballot_number = ballot_number
        self.value = value

    def to_json(self):
        return {
            'type': self.TYPE,
            'ballot_number': self.ballot_number,
            'value': self.value
        }

    @classmethod
    def from_json(cls, j):
        ballot_number = j['ballot_number']
        value = j['value']
        return cls(ballot_number, value)


class AcceptMessage(Message):

    TYPE = 'accept'

    def __init__(self, ballot_number):
        self.ballot_number = ballot_number

    def to_json(self):
        return {
            'type': self.TYPE,
            'ballot_number': self.ballot_number
        }

    @classmethod
    def from_json(cls, j):
        ballot_number = j['ballot_number']
        return cls(ballot_number)


class PeerInfo(MessageNoSignature):

    TYPE = 'peerinfo'

    def __init__(self, vk, ip, port):
        if not isinstance(vk, str):
            vk = vk_to_str(vk)
        self.vk = vk
        self.ip = ip
        self.port = port

    def to_json(self):
        return {
            'type': self.TYPE,
            'vk': self.vk,
            'ip': self.ip,
            'port': self.port
        }

    @classmethod
    def from_json(cls, j):
        vk = j['vk']
        ip = j['ip']
        port = j['port']
        return cls(vk, ip, port)


class DebugInfo(MessageNoSignature):

    TYPE = 'debug'

    def __init__(self, vk, msg):
        self.msg = msg
        if not isinstance(vk, str):
            vk = vk_to_str(vk)
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


class ControllerExitCommand(MessageNoSignature):

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


class ControllerPropagateMessage(MessageNoSignature):
    TYPE = 'propagate'

    def __init__(self, value):
        self.value = value

    def to_json(self):
        return {
            'type': self.TYPE,
            'value': self.value
        }

    @classmethod
    def from_json(cls, j):
        value = j['value']
        return cls(value)
