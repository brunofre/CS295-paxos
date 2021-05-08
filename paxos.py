import socket
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from cryptography.fernet import Fernet


############################### HELPERS #################################

# tcp helpers
def tcp_send_msg(sock, msg):
    msg = struct.pack('>I', len(msg)) + msg
    return sock.sendall(msg)

def tcp_recv_msg(sock):
    raw_msglen = sock.recv(4)
    if raw_msglen is None or len(raw_msglen) < 4:
        return None
    msglen = struct.unpack('>I', raw_msglen)
    r = sock.recvfrom(msglen)
    if len(r[0]) < msglen:
        return None
    return r


# used for passing peers as messages in tcp
def encapsulate_peer(public_key, ip, port):
    return ("PEER;" + public_key.decode("utf-8") + ";" + ip + ";" + str(port)).encode("utf-8")

def decapsulate_peer(peer):
    peer = peer.decode("utf-8").split(";")
    return (peer[1].encode("utf-8"), peer[2], int(peer[3]))


##########################################################################


class Server:

    # each replica is a pubkey -> {ip, port}
    replicas = {}

    def __init__(self, ip, listening_port):
        # opens tcp socket for listening 
        pass

    def new_replica(self, replica):
        # add new replica to replicas[]
        # sends info about it to existing replicas
        pass

    def remove_replica(self, replica):
        pass



class Replica:

    secretsignkey = None
    publicsignkey = None # in bytes

    ip = None
    port = None

    server_ip = None
    server_port = None

    highest_seen_ballot = None

    # each peer is a pubkey -> {ip, port}
    peers = {}

    listen = None # a listening_thread, see below
    
    def __init__(self, server_ip, server_port, listening_port, ip):
        # connects to server and populate peers[]
        # opens udp socket at listening_port using listening_thread

        # TO DO: error checking

        self.ip = ip
        self.port = listening_port

        self.server_ip = server_ip
        self.server_port = server_port

        # pk pair for signing messages during this run of paxos.py, will be used for
        # authenticating the ephemeral public key during key exchange when
        # first contacting another replica
        self.secretsignkey = x25519.X25519PrivateKey.generate()
        self.publicsignkey = self.secretsignkey.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw)

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((server_ip, server_port))

        msg = encapsulate_peer(publicsignkey, ip, listening_port)
     
        tcp_send_msg(s, msg)

        while msg = tcp_recv_msg(s):
            peer = decapsulate_peer(msg)
            peers[peer[0]] = {"ip" : peer[1], "port" : peer[2]}

        listen = self.listening_thread(self.ip, self.port)

        self.watcher()
        

    class listening_thread:
        # how do we do this part, should we span a thread which lets Replicas know when message arrives??
        # it should keep an incoming message log of the highest ballot messages
        # (say with prepared/accepts etc) and give them to the Replica when requested
        log = []
        def __init__(self, ip, port):
            pass

    def choose_value(self, value):
        # tries to become leader and propagates value
        # returns success or not
        pass

    def exchange_sym_keys(self, peer):
        if "symkey" in self.peers[peer]:
            return
    
        # we use ECDH
        # the protocol message for DH is sent signed by our privsignkey
        
        ephemeral_key = x25519.X25519PrivateKey.generate()

        sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)

        msg = ephemeral_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw)

        signature = self.secretsignkey.sign(msg)

        sock.sendto(b"DH MSG;"+self.publicsignkey+b";"+signature+b";"+msg,
                                    (peers[peer]["ip"], peers[peer]["port"]))

        peer_msg = None # TO DO: ask listen for dh msg from peer
        key = ephemeral_key.exchange(ec.ECDH(), peer_msg)
        derived_key = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=None,
                info=b'', # TO DO: add pkeys here, use lexicographic??
                ).derive(key)
        
        peers[peer]["symkey"] = derived_key
        peers[peer]["Fernet"] = Fernet(derived_key) # we can use this directly to encrypt/dec for this peer


    def become_leader(self, ballot):
        # tries to become a leader using ballot number, returns peers that accepted if majority, otherwise False
        # will send prepares in parallel (say 5) through threads, collect outputs (or timeout after some specific dt) and stop
        # when getting majority of prepared

        def send_prepare(peer, ballot):
            exchange_sym_keys(peer) # makes sure we have negotiated ephemeral keys
            # simply sends the prepare message using sym key. Note Fernet gives us authentication already
            pass

        slaves = {} # the ones that prepared

        # randomly sort and send prepares to some peers at once
        # recurse until majority can't be achieved or when it was
        # will probabily run a loop asking listen for how many messages + sleep(0.5)
        # ZZZ: what happens when we get a higher ballot number message?

        if len(slaves) > len(peers)/2: # fix this, probably wrong depending on evenness
            return slaves
        else:
            become_leader(ballot+1) # or return false??

    
    def propose(self, value, slaves):
        # we are a leader, propose a value to slaves

    def watcher(self):
        # decides when to send message..., e.g. by asking for input from user
        pass

    
    def send_accept(self, peer, value):
        #
        pass
