#!/usr/bin/env python3
import socket
import time
import socketserver
import time
import threading


class Party:
    def __init__(self):
        self.HOST, self.PORT = "0.0.0.0", 8888
        proposer_thread = threading.Thread(target=self.proposer)
        acceptor_thread = threading.Thread(target=self.acceptor)
        learner_thread = threading.Thread(target=self.learner)
        proposer_thread.start()
        acceptor_thread.start()
        learner_thread.start()

    def proposer(self):
        pass

    def acceptor(self):
        pass

    def learner(self):
        pass

    def broadcast(self, m):
        server = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

        # Enable port reusage so we will be able to run multiple clients and servers on single (host, port).
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

        # Enable broadcasting mode
        server.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        # Set a timeout so the socket does not block
        # indefinitely when trying to receive data.
        server.settimeout(0.2)
        message = b"your very important message"
        server.sendto(message, ('<broadcast>', 37020))
        print("message sent!")

    def listen(self):
        client = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)  # UDP

        # Enable port reusage so we will be able to run multiple clients and servers on single (host, port).
        client.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)

        # Enable broadcasting mode
        client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        client.bind((self.HOST, self.PORT))
        while True:
            # Thanks @seym45 for a fix
            data, addr = client.recvfrom(1024)
            print("received message: %s" % data)
        pass


if __name__ == "__main__":
    HOST, PORT = "localhost", 9999
    with socketserver.UDPServer((HOST, PORT), PaxosUDPHandler) as server:
        server.serve_forever()
