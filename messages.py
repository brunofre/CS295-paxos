import json


class Message:
    def __init__(self, message):
        self.message = message

    @classmethod
    def from_string(cls, message):
        j = json.load(message)
        payload_string = j['payload_string']
        signature = j['signature']
        vk = j['vk']

        assert vk.verify(signature, payload_string)
        payload = json.load(payload_string)

        if PrepareMessage.is_valid(payload):
            message = PrepareMessage().from_json(payload)
        elif PreparedMessage.is_valid(payload):
            message = PreparedMessage().from_json(payload)
        elif ProposeMessage.is_valid(payload):
            message = ProposeMessage().from_json(payload)
        return cls(message)

    def to_string(self, sk, vk):
        payload_string = json.dump(self.message.to_json())
        signature = sk.sign(payload_string)
        j = {
            'payload_string': payload_string,
            'signature': signature,
            'vk': vk
        }  # checksum? Bruno: i dont think so, it is signed after all...
        return json.dump(j)

class PrepareMessage:
    TYPE = 'prepare'

    @staticmethod
    def is_valid(message):
        j = json.load(message)
        return j['type'] == PrepareMessage.TYPE

    def __init__(self, ballot_number):
        self.ballot_number = ballot_number

    def to_json(self):
        return {
            'type': self.TYPE,
            'ballot_number': self.ballot_number
        }

    @classmethod
    def from_json(cls, message):
        assert(message['type'] == cls.TYPE)
        ballot_number = message['ballot_number']
        return cls(ballot_number)


class PreparedMessage:
    TYPE = 'prepared'

    @staticmethod
    def is_valid(message):
        j = json.load(message)
        return j['type'] == PrepareMessage.TYPE

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

    @staticmethod
    def is_valid(message):
        j = json.load(message)
        return j['type'] == PrepareMessage.TYPE

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

    @staticmethod
    def is_valid(message):
        j = json.load(message)
        return j['type'] == PrepareMessage.TYPE

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

    @staticmethod
    def is_valid(message):
        j = json.load(message)
        return j['type'] == PeerInfo.TYPE

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

    def to_string(self):
        return json.dump(self.to_json())

    @staticmethod
    def from_string(str):
        return PeerInfo().from_json(json.load(str))

    @classmethod
    def from_json(cls, j):
        assert(j['type'] == cls.TYPE)
        vk = j['vk']
        ip = j['ip']
        port = j['port']
        return cls(pkey, ip, port)

class DebugInfo:
    TYPE = 'debug'

    @staticmethod
    def is_valid(message):
        j = json.load(message)
        return j['type'] == DebugInfo.TYPE

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
        #j = json.load(j) ??
        assert(j['type'] == cls.TYPE)
        msg = j['msg']
        vk = j['vk']
        return cls(pkey, msg)
