from messages import PeerInfo,DebugInfo

# TO DO: handle strings in recv/send
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

class Coordinator:

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
