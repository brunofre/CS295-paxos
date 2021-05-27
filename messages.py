import json
import socket
import base64

def vk_to_str(vk):
    return base64.b64encode(vk.to_string()).decode("ascii")
def str_to_vk(st):
    return base64.b64decode(st.encode("utf-8"))

class Message:
    def __init__(self, message):
        self.message = message # needs to provide to_json, from_json

    @classmethod
    def from_string(cls, message):
        j = json.load(message)
        payload_string = j['payload_string']
        signature = j['signature']
        vk = str_to_vk(j['vk'])

        assert vk.verify(signature, payload_string)
        payload = json.load(payload_string)
        
        if PrepareMessage.is_valid(payload_string):
            message = PrepareMessage().from_json(payload)
        elif PreparedMessage.is_valid(payload_string):
            message = PreparedMessage().from_json(payload)
        elif ProposeMessage.is_valid(payload_string):
            message = ProposeMessage().from_json(payload)
        return cls(message)

    def to_string(self, sk, vk):
        payload_string = json.dump(self.message.to_json())
        if not isinstance(vk, str):
            vk = vk_to_str(vk)
        signature = sk.sign(payload_string)
        j = {
            'payload_string': payload_string,
            'signature': signature,
            'vk': vk
        } 
        return json.dump(j)

    def send_with_udp(self, target_ip, target_port):
        msg = self.to_string()
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
        s.sendto(msg, (target_ip, target_port))
        s.close()

class PrepareMessage:
    TYPE = 'prepare'

    @classmethod
    def is_valid(cls, message):
        j = json.loads(message)
        return j['type'] == cls.TYPE

    def __init__(self, ballot_number):
        self.ballot_number = ballot_number

    def to_json(self):
        return {
            'type': self.TYPE,
            'ballot_number': self.ballot_number
        }

    @classmethod
    def from_json(cls, j):
        assert(j['type'] == cls.TYPE)
        ballot_number = j['ballot_number']
        return cls(ballot_number)


class PreparedMessage:
    TYPE = 'prepared'

    @classmethod
    def is_valid(cls, message):
        j = json.loads(message)
        return j['type'] == cls.TYPE

    def __init__(self, propose_messages):
        self.propose_messages = propose_messages

    def to_json(self):
        return {
            'type': self.TYPE,
            'propose_messages': [propose_message.to_json() for propose_message in self.propose_messages]
        }

    @classmethod
    def from_json(cls, j):
        assert(j['type'] == cls.TYPE)
        propose_messages = [PrepareMessage().from_json(
            propose_message) for propose_message in j['propose_messages']]
        return cls(propose_messages)


class ProposeMessage:
    TYPE = 'propose'

    @classmethod
    def is_valid(cls, message):
        j = json.loads(message)
        return j['type'] == cls.TYPE

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
        assert(j['type'] == cls.TYPE)
        ballot_number = j['ballot_number']
        value = j['value']
        return cls(ballot_number, value)


class AcceptMessage:
    TYPE = 'accept'

    @classmethod
    def is_valid(cls, message):
        j = json.loads(message)
        return j['type'] == cls.TYPE

    def __init__(self, ballot_number):
        self.ballot_number = ballot_number

    def to_json(self):
        return {
            'type': self.TYPE,
            'ballot_number': self.ballot_number
        }

    @classmethod
    def from_json(cls, j):
        assert(j['type'] == cls.TYPE)
        ballot_number = j['ballot_number']
        return cls(ballot_number)

class PeerInfo:
    TYPE = 'peerinfo'

    @classmethod
    def is_valid(cls, message):
        j = json.loads(message)
        return j['type'] == cls.TYPE

    def __init__(self, vk, ip, port):
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
        assert(j['type'] == cls.TYPE)
        vk = j['vk']
        ip = j['ip']
        port = j['port']
        return cls(vk, ip, port)

    # we need to/from string since we don't want to sign these messages as class Message does
    def to_string(self):
        return json.dumps(self.to_json())

    @classmethod
    def from_string(cls, s):
        if isinstance(s, bytes):
            s = s.decode("utf-8")
        return cls.from_json(json.loads(s))

    

class DebugInfo:
    TYPE = 'debug'

    @classmethod
    def is_valid(cls, message):
        j = json.loads(message)
        return j['type'] == cls.TYPE

    def __init__(self, vk, msg):
        self.msg = msg
        self.vk = vk

    def to_json(self):
        return {
            'type': self.TYPE,
            'vk': self.vk, # we are using vk as an ID
            'msg': self.msg
        }

    @classmethod
    def from_json(cls, j):
        assert(j['type'] == cls.TYPE)
        msg = j['msg']
        vk = j['vk']
        return cls(vk, msg)

class ControllerExitCommand:
    TYPE = 'exit'

    @classmethod
    def is_valid(cls, message):
        j = json.loads(message)
        return j['type'] == cls.TYPE

    def __init__(self):
        pass

    def to_json(self):
        return {
            'type': self.TYPE,
        }

    @classmethod
    def from_json(cls, j):
        assert(j['type'] == cls.TYPE)
        return cls()

    def to_string(self):
        msg = json.dumps(self.to_json())
        return msg

    @classmethod
    def from_string(cls, s):
        if isinstance(s, bytes):
            s = s.decode("utf-8")
        return cls.from_json(json.loads(s))

class ControllerPropagateMessage:
    TYPE = 'propagate'

    @staticmethod
    def is_valid(message):
        j = json.loads(message)
        return j['type'] == PrepareMessage.TYPE

    def __init__(self, value):
        self.value = value

    def to_json(self):
        return {
            'type': self.TYPE,
            'value': self.value
        }

    @classmethod
    def from_json(cls, j):
        assert(j['type'] == cls.TYPE)
        value = j['value']
        return cls(value)

    @classmethod
    def from_string(cls, s):
        if isinstance(s, bytes):
            s = s.decode("utf-8")
        return cls.from_json(json.loads(s))

    def to_string(self):
        msg = json.dumps(self.to_json())
        return msg
