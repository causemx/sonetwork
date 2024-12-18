import socket
import json
import time
import threading
from PyQt5.QtCore import QObject, pyqtSignal

class NetworkMonitorSignals(QObject):
    """Signal handler for network monitoring events"""
    connection_changed = pyqtSignal(tuple)  # (node1_id, node2_id, is_connected)
    monitoring_update = pyqtSignal(str)  # timestamp of the monitoring update

class NetworkMonitor:
    """
    Monitors connections between network nodes and updates network topology
    """
    def __init__(self, base_port=5000):
        self.base_port = base_port
        self.nodes = {}  # {node_id: (host, port)}
        self.connections = set()  # Set of (node1_id, node2_id) tuples
        self.running = False
        self.monitor_thread = None
        self.signals = NetworkMonitorSignals()
        
    def start_monitoring(self, nodes):
        """Start monitoring the provided nodes"""
        self.nodes = nodes
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_connections, daemon=True)
        self.monitor_thread.start()
        
    def stop_monitoring(self):
        """Stop the monitoring process"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
            
    def _check_connection(self, node1_id, node2_id):
        """Check if two nodes can communicate with each other"""
        try:
            # Create a temporary socket for testing
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            test_socket.settimeout(0.5)  # Short timeout for quick checks
            
            # Prepare test message
            message = {
                'type': 'connection_test',
                'from_id': node1_id,
                'timestamp': time.time()
            }
            
            # Get node addresses
            node1_host, node1_port = self.nodes[node1_id]
            node2_host, node2_port = self.nodes[node2_id]
            
            # Try to send message
            test_socket.sendto(json.dumps(message).encode(), (node2_host, node2_port))
            
            # Try to receive response
            try:
                data, addr = test_socket.recvfrom(1024)
                response = json.loads(data.decode())
                if response.get('type') == 'connection_test_response':
                    return True
            except (socket.timeout, json.JSONDecodeError):
                return False
            finally:
                test_socket.close()
                
        except Exception as e:
            print(f"Error checking connection between nodes {node1_id} and {node2_id}: {e}")
            return False
            
        return False
        
    def _monitor_connections(self):
        """Continuously monitor connections between all nodes"""
        while self.running:
            current_connections = set()
            
            # Emit monitoring update signal with current timestamp
            timestamp = time.strftime('%H:%M:%S')
            self.signals.monitoring_update.emit(timestamp)
            
            # Check all possible node pairs
            node_ids = list(self.nodes.keys())
            for i, node1_id in enumerate(node_ids):
                for node2_id in node_ids[i + 1:]:
                    # Check if nodes can communicate
                    is_connected = self._check_connection(node1_id, node2_id)
                    
                    # Store connection if exists
                    if is_connected:
                        current_connections.add(tuple(sorted([node1_id, node2_id])))
                    
                    # Emit signal if connection status changed
                    connection = tuple(sorted([node1_id, node2_id]))
                    was_connected = connection in self.connections
                    if is_connected != was_connected:
                        self.signals.connection_changed.emit((node1_id, node2_id, is_connected))
            
            # Update stored connections
            self.connections = current_connections
            
            # Wait before next check
            time.sleep(5)  # 5-second refresh interval
            
    def get_active_connections(self):
        """Return the current set of active connections"""
        return self.connections.copy()