import socket
import threading
import time
import random
import json

class Node:
    def __init__(self, node_id, host='localhost', base_port=5000):
        self.id = node_id
        self.host = host
        self.port = base_port + node_id
        self.is_master = (node_id == 0)
        self.peers = {}  # {node_id: (host, port)}
        self.master_id = 0
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((host, self.port))
        self.address = f"{host}:{self.port}"
        self.alive = True

    def start(self):
        # Initialize peer connections
        for i in range(10):
            if i != self.id:
                self.peers[i] = (self.host, 5000 + i)

        # Start listening thread
        threading.Thread(target=self._listen, daemon=True).start()

        # Start heartbeat thread
        if self.is_master:
            threading.Thread(target=self._send_heartbeat, daemon=True).start()
        else:
            threading.Thread(target=self._monitor_master, daemon=True).start()

    def _listen(self):
        while self.alive:
            try:
                data, addr = self.socket.recvfrom(1024)
                message = json.loads(data.decode())
                self._handle_message(message, addr)
            except Exception as e:
                print(f"Node {self.id} error: {e}")

    def _handle_message(self, message, addr):
        msg_type = message.get('type')

        if msg_type == 'heartbeat':
            if not self.is_master:
                self.last_heartbeat = time.time()

        elif msg_type == 'master_election':
            if not self.is_master:
                proposed_master = message.get('proposed_master')
                if proposed_master > self.id:
                    # Forward the election message
                    self._broadcast_message(message)
                elif proposed_master < self.id:
                    # Propose self as master
                    self._initiate_election()

    def _send_heartbeat(self):
        while self.alive and self.is_master:
            message = {
                'type': 'heartbeat',
                'master_id': self.id,
                'timestamp': time.time()
            }
            self._broadcast_message(message)
            time.sleep(1)

    def _monitor_master(self):
        self.last_heartbeat = time.time()
        while self.alive and not self.is_master:
            if time.time() - self.last_heartbeat > 3:  # Master timeout
                self._initiate_election()
            time.sleep(1)

    def _initiate_election(self):
        message = {
            'type': 'master_election',
            'proposed_master': self.id,
            'timestamp': time.time()
        }
        self._broadcast_message(message)

    def _broadcast_message(self, message):
        for node_id, (host, port) in self.peers.items():
            try:
                data = json.dumps(message).encode()
                self.socket.sendto(data, (host, port))
            except Exception as e:
                print(f"Error sending to node {node_id}: {e}")

    def stop(self):
        self.alive = False
        self.socket.close()

def run_network():
    nodes = []
    # Create and start nodes
    for i in range(10):
        node = Node(i)
        node.start()
        nodes.append(node)
        print(f"Started node {i} {'(Master)' if i == 0 else '(Slave)'}")

    try:
        while True:
            time.sleep(1)
            # Simulate random master disconnection
            if random.random() < 0.01:  # 1% chance each second
                master_node = next(n for n in nodes if n.is_master)
                print(f"\nDisconnecting master node {master_node.id}")
                master_node.stop()
                nodes.remove(master_node)
    except KeyboardInterrupt:
        for node in nodes:
            node.stop()

if __name__ == "__main__":
    run_network()
