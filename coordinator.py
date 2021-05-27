import struct
import socket
import thread
from messages import Message,PeerInfo,DebugInfo

def tcp_send_msg(sock, msg):
    if isinstance(msg, str):
        msg = msg.encode("utf-8")
    msg = struct.pack('>I', len(msg)) + msg
    return sock.sendall(msg)

def tcp_recv_msg(sock):
    raw_msglen = sock.recv(4)
    assert not (raw_msglen is None or len(raw_msglen) < 4)
    msglen = struct.unpack('>I', raw_msglen)
    r = sock.recvfrom(msglen)
    assert len(r[0]) == msglen
    return {"data":r[0].decode("utf-8"), "from":r[1]}

class Coordinator:

    # each replica is a pubkey -> {ip, port} where port is UDP
    replicas = {}

    def __init__(self, ip, listening_port):
        # opens tcp socket and spans threads
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.bind((ip, listening_port))
        self.s.listen(5)

        while True:
            (clientsocket, address) = self.s.accept()
            thread.start_new_thread(self.client_thread, (clientsocket,))
            
    def client_thread(self, c):
        msg = tcp_recv_msg(c)
        data, addr = msg["data"], msg["from"]

        if PeerInfo.is_valid(data): # this is a new peer
            # first gets replica info from the msg
            info = PeerInfo.from_string(data)
            # then sends prev replicas to this one
            for vk, r in self.replicas.items():
                pinfo = PeerInfo.from_json({"vk":vk, "ip":r["ip"], "port":r["port"]}).to_string()
                tcp_send_msg(c, pinfo)
            j = info.to_json()
            self.replicas[j["vk"]] = {"ip":j["ip"], "port":j["port"]}                
            # now let older replicas know of the new one
            self.spread_new_replica(info)
        elif DebugInfo.is_valid(data): # initializes debug socket for incoming messages/controlling
            j = data.to_json()
            self.replicas[j["vk"]]["debug_socket"] = c
        else:
            pass

    def spread_new_replica(self, info):
        j = info.to_json()
        for vk, rep in self.replicas.items():
            if vk != j["vk"]:
                s = rep["debug_socket"]
                m = Message(info).to_string()
                tcp_send_msg(s, m)
