# Import required libraries
import sys
import math
import random
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QPushButton, QLabel, QStatusBar)
from PyQt5.QtCore import QTimer
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

# NetworkNode class definition
class NetworkNode:
    """
    Represents a node in the network with basic properties and state
    """
    def __init__(self, node_id, host='localhost', base_port=5000):
        self.id = node_id
        self.host = host
        self.port = base_port + node_id
        self.is_master = (node_id == 0)  # First node is initially the master
        self.address = f"{host}:{self.port}"
        self.peers = {}  # Dictionary to store peer connections
        self.master_id = 0
        self.is_active = True

# Main Window class
class NetworkVisualizerWindow(QMainWindow):
    """
    Main window class for the network visualizer application
    """
    def __init__(self):
        super().__init__()
        # Set window properties
        self.setWindowTitle("Self-Organizing Network Visualizer")
        self.setGeometry(100, 100, 1400, 900)  # x, y, width, height
        
        # Initialize network components
        self.nodes = {}  # Dictionary to store network nodes
        self.network_graph = nx.Graph()  # NetworkX graph for visualization
        self.master_node = 0  # ID of current master node
        
        # Calculate static positions for nodes in a circle
        self.node_positions = self._calculate_node_positions()
        
        # Set up the main window layout
        self._setup_main_layout()
        
        # Initialize the network
        self._setup_network()
        
        # Set up update timer for periodic refresh
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_visualization)
        self.update_timer.start(1000)  # Update every second

    def _setup_main_layout(self):
        """Initialize the main window layout"""
        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        
        # Add control panel
        control_panel = self._create_control_panel()
        layout.addWidget(control_panel)
        
        # Add network visualization
        self.figure, self.ax = plt.subplots(figsize=(10, 8))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas, stretch=2)
        
        # Add status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

    def _calculate_node_positions(self):
        """Calculate positions for nodes in a circle layout"""
        positions = {}
        num_nodes = 10
        radius = 0.8  # Circle radius
        center = (1.0, 1.0)  # Center point
        
        for i in range(num_nodes):
            # Calculate angle and position for each node
            angle = 2 * math.pi * i / num_nodes
            x = center[0] + radius * math.cos(angle)
            y = center[1] + radius * math.sin(angle)
            positions[i] = (x, y)
            
        return positions

    def _create_control_panel(self):
        """Create the control panel with network information and controls"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        panel.setMinimumWidth(250)

        # Add Network Status section
        self._add_status_section(layout)
        
        # Add Node List section
        self._add_node_list_section(layout)
        
        # Add Control Buttons section
        self._add_control_buttons(layout)
        
        # Add Legend section
        self._add_legend_section(layout)
        
        layout.addStretch()
        return panel

    def _add_status_section(self, layout):
        """Add network status information section"""
        status_group = QWidget()
        status_layout = QVBoxLayout(status_group)
        
        # Add title
        title_label = QLabel("Network Status")
        title_label.setStyleSheet("""
            font-weight: bold;
            font-size: 14px;
            padding: 5px;
            background-color: #f0f0f0;
            border-radius: 5px;
        """)
        status_layout.addWidget(title_label)
        
        # Add status labels
        self.master_label = QLabel("Master: localhost:5000")
        self.active_nodes_label = QLabel("Active Nodes: 10")
        status_layout.addWidget(self.master_label)
        status_layout.addWidget(self.active_nodes_label)
        layout.addWidget(status_group)

    def _add_node_list_section(self, layout):
        """Add section showing list of all nodes"""
        nodes_group = QWidget()
        nodes_layout = QVBoxLayout(nodes_group)
        
        nodes_title = QLabel("Node List")
        nodes_title.setStyleSheet("""
            font-weight: bold;
            font-size: 14px;
            padding: 5px;
            background-color: #f0f0f0;
            border-radius: 5px;
        """)
        nodes_layout.addWidget(nodes_title)
        
        self.nodes_list = QLabel()
        self.nodes_list.setStyleSheet("""
            padding: 5px;
            background-color: white;
            border: 1px solid #ddd;
            border-radius: 5px;
        """)
        nodes_layout.addWidget(self.nodes_list)
        layout.addWidget(nodes_group)

    def _add_control_buttons(self, layout):
        """Add control buttons section"""
        buttons_group = QWidget()
        buttons_layout = QVBoxLayout(buttons_group)
        
        # Add title
        controls_label = QLabel("Controls")
        controls_label.setStyleSheet("""
            font-weight: bold;
            font-size: 14px;
            padding: 5px;
            background-color: #f0f0f0;
            border-radius: 5px;
        """)
        buttons_layout.addWidget(controls_label)
        
        # Button style
        button_style = """
            QPushButton {
                background-color: #f8f9fa;
                border: 2px solid #dee2e6;
                border-radius: 5px;
                padding: 8px;
                margin: 2px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-color: #ced4da;
            }
            QPushButton:pressed {
                background-color: #dee2e6;
            }
        """
        
        # Create and add buttons
        kill_master_btn = QPushButton("Kill Master Node")
        kill_random_btn = QPushButton("Kill Random Node")
        restore_btn = QPushButton("Restore Network")
        
        for btn in [kill_master_btn, kill_random_btn, restore_btn]:
            btn.setStyleSheet(button_style)
        
        kill_master_btn.clicked.connect(self._kill_master_node)
        kill_random_btn.clicked.connect(self._kill_random_node)
        restore_btn.clicked.connect(self._restore_network)
        
        buttons_layout.addWidget(kill_master_btn)
        buttons_layout.addWidget(kill_random_btn)
        buttons_layout.addWidget(restore_btn)
        layout.addWidget(buttons_group)

    def _add_legend_section(self, layout):
        """Add legend explaining node colors"""
        legend_group = QWidget()
        legend_layout = QVBoxLayout(legend_group)
        
        legend_label = QLabel("Legend")
        legend_label.setStyleSheet("""
            font-weight: bold;
            font-size: 14px;
            padding: 5px;
            background-color: #f0f0f0;
            border-radius: 5px;
        """)
        legend_layout.addWidget(legend_label)
        
        master_legend = QLabel("● Red - Master Node")
        master_legend.setStyleSheet("color: red; padding: 5px;")
        slave_legend = QLabel("● Blue - Slave Node")
        slave_legend.setStyleSheet("color: blue; padding: 5px;")
        
        legend_layout.addWidget(master_legend)
        legend_layout.addWidget(slave_legend)
        layout.addWidget(legend_group)

    def _setup_network(self):
        """Initialize the network with nodes and connections"""
        # Create nodes
        for i in range(10):
            node = NetworkNode(i)
            self.nodes[i] = node
            self.network_graph.add_node(i)
        
        # Create edges (fully connected network)
        for i in range(10):
            for j in range(i + 1, 10):
                self.network_graph.add_edge(i, j)
        
        self._update_visualization()

    def _update_visualization(self):
        """Update the network visualization and status information"""
        self.ax.clear()
        
        # Prepare node visualization properties
        node_colors = []
        node_sizes = []
        for node_id in self.network_graph.nodes():
            if node_id == self.master_node:
                node_colors.append('red')
                node_sizes.append(2000)  # Larger size for master
            else:
                node_colors.append('lightblue')
                node_sizes.append(1500)  # Normal size for slaves
        
        # Draw nodes
        nx.draw_networkx_nodes(self.network_graph, 
                             self.node_positions,
                             node_color=node_colors,
                             node_size=node_sizes)
        
        # Draw edges
        nx.draw_networkx_edges(self.network_graph, 
                             self.node_positions,
                             edge_color='gray',
                             alpha=0.3,
                             width=0.5)
        
        # Draw labels with IP:Port
        labels = {node_id: f"{self.nodes[node_id].address}" 
                 for node_id in self.network_graph.nodes()}
        nx.draw_networkx_labels(self.network_graph, 
                              self.node_positions,
                              labels,
                              font_size=8)
        
        # Set visualization properties
        self.ax.set_title("Network Topology", pad=20, fontsize=14)
        self.ax.set_xlim(0, 2)
        self.ax.set_ylim(0, 2)
        self.canvas.draw()
        
        # Update status information
        self._update_status_info()

    def _update_status_info(self):
        """Update status labels and node list"""
        # Update master info
        master_node = next((node for node in self.nodes.values() if node.is_master), None)
        if master_node:
            self.master_label.setText(f"Master: {master_node.address}")
        
        # Update active nodes count
        self.active_nodes_label.setText(f"Active Nodes: {len(self.nodes)}")
        
        # Update nodes list
        nodes_text = ""
        for node in sorted(self.nodes.values(), key=lambda x: x.port):
            status = "Master" if node.is_master else "Slave"
            nodes_text += f"{node.address} ({status})\n"
        self.nodes_list.setText(nodes_text)

    def _kill_master_node(self):
        """Handler for Kill Master Node button"""
        if self.nodes:
            master_node = next((node for node in self.nodes.values() if node.is_master), None)
            if master_node:
                self._kill_node(master_node.id)
                self.statusBar.showMessage(f"Killed master node {master_node.address}")

    def _kill_random_node(self):
        """Handler for Kill Random Node button"""
        if self.nodes:
            node_to_kill = random.choice(list(self.nodes.values()))
            self._kill_node(node_to_kill.id)
            self.statusBar.showMessage(f"Killed node {node_to_kill.address}")

    def _kill_node(self, node_id):
        """Remove a node from the network and handle master election if needed"""
        if node_id in self.nodes:
            node = self.nodes[node_id]
            node.is_active = False
            del self.nodes[node_id]
            self.network_graph.remove_node(node_id)
            
            # If master was killed, elect new master (highest remaining ID)
            if node.is_master:
                remaining_ids = list(self.nodes.keys())
                if remaining_ids:
                    new_master_id = max(remaining_ids)
                    self.master_node = new_master_id
                    for node in self.nodes.values():
                        if node.id == new_master_id:
                            node.is_master = True
                        else:
                            node.is_master = False

    def _restore_network(self):
        """Handler for Restore Network button"""
        self.nodes.clear()
        self.network_graph.clear()
        self._setup_network()
        self.statusBar.showMessage("Network restored")

    def closeEvent(self, event):
        """Handle application close event"""
        super().closeEvent(event)

# Main application entry point
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Use Fusion style for modern look
    window = NetworkVisualizerWindow()
    window.show()
    sys.exit(app.exec_())