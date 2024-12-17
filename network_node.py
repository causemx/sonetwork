import socket
import threading
import time
import json
import re
from PyQt5.QtCore import QObject, pyqtSignal

class NetworkSignals(QObject):
    """Signal handler for network events"""
    master_changed = pyqtSignal(int)  # Emitted when master node changes
    node_died = pyqtSignal(int)  # Emitted when a node dies

class NetworkNode:
    """
    Represents a node in the network with both visualization and networking capabilities
    """
    def __init__(self, host='localhost', port=None, is_master=False, base_port=5000):
         # Basic properties
        self.host = host
        self.port = port
        self.is_master = is_master
        self.address = f"{host}:{self.port}"
        self.is_active = True
        self.id = self.port - base_port
        
        # Network properties
        self.peers = {}
        self.master_id = 0 if is_master else None
        self.socket = None  # Initialize socket as None
        self.alive = True
        self.last_heartbeat = time.time()
        
        # Qt signals
        self.signals = NetworkSignals()
        self._cleanup_in_progress = False
        
        # Initialize socket
        self._create_socket()

    def _create_socket(self):
        """Create and bind the socket with error handling"""
        try:
            if self.socket is not None:
                try:
                    self.socket.close()
                except Exception:
                    pass
            
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                # Try to bind to the port
                self.socket.bind((self.host, self.port))
            except OSError as e:
                print(f"Failed to bind to port {self.port}: {e}, retrying in 1 second...")
                time.sleep(1)
                self.socket.bind((self.host, self.port))
        except Exception as e:
            print(f"Error creating socket for node {self.id}: {e}")
            raise

    def _calculate_host_id(self, host):
        """Calculate node ID based on sum of numerical values in host address"""
        numbers = re.findall(r'\d+', host)
        return sum(int(num) for num in numbers) if numbers else 0

    def start(self):
        """Start the node's network operations"""
        # Initialize peer connections
        for peer_config in self.config.get('network', {}).get('nodes', []):
            peer_id = self._calculate_host_id(peer_config['host'])
            if peer_id != self.id:
                self.peers[peer_id] = (peer_config['host'], peer_config['port'])

        # Start listening thread
        threading.Thread(target=self._listen, daemon=True).start()

        # Start appropriate monitoring thread
        if self.is_master:
            threading.Thread(target=self._send_heartbeat, daemon=True).start()
        else:
            threading.Thread(target=self._monitor_master, daemon=True).start()

    def _listen(self):
        """Listen for incoming network messages"""
        while self.alive:
            try:
                data, addr = self.socket.recvfrom(1024)
                message = json.loads(data.decode())
                self._handle_message(message, addr)
            except Exception as e:
                if self.alive:  # Only print if not deliberately stopped
                    print(f"Node {self.id} error: {e}")

    def _handle_message(self, message, addr):
        """Handle received network messages"""
        msg_type = message.get('type')

        if msg_type == 'heartbeat':
            if not self.is_master:
                self.last_heartbeat = time.time()
                # Update master information
                new_master_id = message.get('master_id')
                if new_master_id != self.master_id:
                    self.master_id = new_master_id
                    self.signals.master_changed.emit(new_master_id)

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
        """Send periodic heartbeat messages if master"""
        while self.alive and self.is_master:
            message = {
                'type': 'heartbeat',
                'master_id': self.id,
                'timestamp': time.time()
            }
            self._broadcast_message(message)
            time.sleep(1)

    def _monitor_master(self):
        """Monitor master node's heartbeat"""
        while self.alive and not self.is_master:
            if time.time() - self.last_heartbeat > 3:  # Master timeout
                self._initiate_election()
            time.sleep(1)

    def _initiate_election(self):
        """Start master election process"""
        message = {
            'type': 'master_election',
            'proposed_master': self.id,
            'timestamp': time.time()
        }
        self._broadcast_message(message)

    def _broadcast_message(self, message):
        """Broadcast message to all peers"""
        for node_id, (host, port) in self.peers.items():
            try:
                data = json.dumps(message).encode()
                self.socket.sendto(data, (host, port))
            except Exception as e:
                if self.alive:  # Only print if not deliberately stopped
                    print(f"Error sending to node {node_id}: {e}")

    def stop(self):
        """Stop the node's network operations"""
        if not self._cleanup_in_progress:
            self._cleanup_in_progress = True
            self.alive = False
            self.is_active = False
            
            # Close socket
            if self.socket:
                try:
                    self.socket.shutdown(socket.SHUT_RDWR)
                except Exception:
                    pass
                try:
                    self.socket.close()
                except Exception:
                    pass
                self.socket = None
            
            # Emit signal only if not already cleaning up
            if not self._cleanup_in_progress:
                self.signals.node_died.emit(self.id)
            
            self._cleanup_in_progress = False

    def set_config(self, config):
        """Set network configuration"""
        self.config = config