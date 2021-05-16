import json
import Crypto


class Message:
    def __init__(self, message):
        self.message = message

    @classmethod
    def from_string(cls, message):
        j = json.load(message)
        payload = j['payload']
        signature = j['signature']
        vk = j['vk']

        assert vk.verify(signature, payload)

        if PrepareMessage.is_valid(payload):
            message = PrepareMessage().from_string()
        elif ProposeMessage.is_valid(payload):
            message = ProposeMessage().from_string()
        return cls(message)

    def to_string(self, sk, vk):
        signature = sk.sign(self.message.to_string())
        j = {
            'payload': self.message.to_string(),
            'signature': signature,
            'vk': vk
        }
        return json.dump(j)


class PrepareMessage:
    TYPE = 'prepare'

    @staticmethod
    def is_valid(message):
        j = json.load(message)
        return j['type'] == PrepareMessage.TYPE

    def __init__(self, ballot_number):
        self.ballot_number = ballot_number

    def to_string(self):
        m = {
            'type': self.TYPE,
            'public_key': self.public_key,
            'ballot_number': self.ballot_number
        }
        return json.dump(m)

    @classmethod
    def from_string(cls, message):
        j = json.load(message)
        assert(j['type'] == cls.TYPE)
        ballot_number = j['ballot_number']
        return cls(ballot_number)


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
        j = {
            'type': self.TYPE,
            'ballot_number': self.ballot_number,
            'value': self.value
        }
        return j

    def to_string(self):
        return json.dump(self.to_json())

    @classmethod
    def from_string(cls, message):
        j = json.load(message)
        assert(j['type'] == cls.TYPE)
        ballot_number = j['ballot_number']
        value = j['value']
        return cls(ballot_number, value)


class Accept:
    def __init__(self):
        pass
