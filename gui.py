# Import required libraries
import sys
import random
import json
import time
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QStatusBar,
)
from PyQt5.QtCore import QTimer
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from network_node import NetworkNode


class NetworkVisualizerWindow(QMainWindow):
    """
    Main window class for the network visualizer application
    """

    def __init__(self, config_file="network_config.json"):
        super().__init__()
        # Set window properties
        self.setWindowTitle("Self-Organizing Network Visualizer")
        self.setGeometry(100, 100, 1400, 900)

        # Load drone images
        try:
            self.leader_img = plt.imread("drone_leader.png")
            self.follower_img = plt.imread("drone_follower.png")
        except Exception as e:
            print(f"Error loading drone images: {e}")
            # Fallback to simple shapes if images can't be loaded
            self.leader_img = None
            self.follower_img = None

        # Initialize network components
        self.nodes = {}
        self.network_graph = nx.Graph()
        self.master_node = None

        # Load network configuration
        self.config = self._load_config(config_file)

        # Calculate static positions for nodes in a circle
        self.node_positions = None  # Will be calculated after nodes are created

        # Set up the main window layout
        self._setup_main_layout()

        # Initialize the network
        self._setup_network()

        # Set up update timer for periodic refresh
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_visualization)
        self.update_timer.start(1000)

    def _load_config(self, config_file):
        """Load network configuration from JSON file"""
        try:
            with open(config_file, "r") as f:
                config = json.load(f)
            return config
        except Exception as e:
            print(f"Error loading configuration: {e}")

    def _calculate_pyramid_layers(self, num_nodes):
        """Calculate how many nodes should be in each layer of the pyramid"""
        layers = []
        nodes_left = num_nodes - 1  # Excluding master node
        current_layer = 1

        while nodes_left > 0:
            nodes_in_layer = min(current_layer * 2 - 1, nodes_left)
            layers.append(nodes_in_layer)
            nodes_left -= nodes_in_layer
            current_layer += 1

        return layers

    def _calculate_node_positions(self):
        """Calculate positions for nodes in a rectangular grid layout"""
        positions = {}
        num_nodes = len(self.nodes)
        
        if num_nodes == 0:
            return positions
            
        # Calculate grid dimensions
        # Try to make the grid as square as possible
        grid_cols = int(num_nodes ** 0.5)  # square root rounded down
        if grid_cols < 1:
            grid_cols = 1
        grid_rows = (num_nodes + grid_cols - 1) // grid_cols  # Ceiling division
        
        # Calculate spacing
        margin = 0.2  # margin from edges
        spacing_x = (2.0 - 2 * margin) / max(grid_cols - 1, 1)
        spacing_y = (2.0 - 2 * margin) / max(grid_rows - 1, 1)
        
        # Place nodes in grid
        node_list = sorted(self.nodes.keys())  # Sort nodes by ID
        for i, node_id in enumerate(node_list):
            row = i // grid_cols
            col = i % grid_cols
            
            # Calculate position with margin
            x = margin + col * spacing_x
            y = margin + (grid_rows - 1 - row) * spacing_y  # Invert y to start from top
            
            positions[node_id] = (x, y)
        
        return positions

    def _setup_main_layout(self):
        """Initialize the main window layout"""
        # Create main widget and layout
        main_widget = QWidget()
        main_widget.setStyleSheet("background-color: white;")
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

        title_label = QLabel("Network Status")
        title_label.setStyleSheet("""
            font-weight: bold;
            font-size: 14px;
            padding: 5px;
            background-color: #f0f0f0;
            border-radius: 5px;
        """)
        status_layout.addWidget(title_label)

        self.master_label = QLabel("Master: Not Selected")
        self.active_nodes_label = QLabel("Active Nodes: 0")
        self.master_label.setStyleSheet("color: black;")
        self.active_nodes_label.setStyleSheet("color: black;")
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
            color: black;
        """)
        nodes_layout.addWidget(self.nodes_list)
        layout.addWidget(nodes_group)

    def _add_control_buttons(self, layout):
        """Add control buttons section"""
        buttons_group = QWidget()
        buttons_layout = QVBoxLayout(buttons_group)

        controls_label = QLabel("Controls")
        controls_label.setStyleSheet("""
            font-weight: bold;
            font-size: 14px;
            padding: 5px;
            background-color: #f0f0f0;
            border-radius: 5px;
            color: black;
        """)
        buttons_layout.addWidget(controls_label)

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
        """Initialize the network with nodes and connections from config"""
        # Create a list of nodes to stop
        nodes_to_stop = list(self.nodes.values())
        
        # Stop all existing nodes without triggering signals
        for node in nodes_to_stop:
            if hasattr(node, "stop"):
                node._cleanup_in_progress = True
                node.stop()
        
        # Clear existing network
        self.nodes.clear()
        self.network_graph.clear()
        
        # Add a small delay to ensure ports are released
        time.sleep(1)

        # Create nodes from configuration
        for node_config in self.config["network"]["nodes"]:
            try:
                node = NetworkNode(
                    host=node_config["host"],
                    port=node_config["port"],
                    is_master=node_config["is_master"],
                    base_port=self.config["network"]["base_port"]
                )
                # Set up signals
                node.signals.master_changed.connect(self._handle_master_change)
                node.signals.node_died.connect(self._handle_node_death)

                # Initialize and start the node
                node.set_config(self.config)
                node.start()

                self.nodes[node.id] = node
                self.network_graph.add_node(node.id)

                if node.is_master:
                    self.master_node = node.id
                    
            except Exception as e:
                print(f"Error creating node: {e}")
                continue

        # Calculate node positions after creating nodes
        self.node_positions = self._calculate_node_positions()

        # Create edges for nearby nodes instead of fully connected
        node_ids = list(self.nodes.keys())
        positions = self._calculate_node_positions()
        
        # Calculate edges based on proximity
        for i, node1_id in enumerate(node_ids):
            for j, node2_id in enumerate(node_ids[i+1:], i+1):
                # Calculate distance between nodes
                pos1 = positions[node1_id]
                pos2 = positions[node2_id]
                distance = ((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)**0.5
                
                # Add edge if nodes are close enough (adjacent in grid)
                if distance < 0.5:  # Adjust this threshold as needed
                    self.network_graph.add_edge(node1_id, node2_id)

        self._update_visualization()

    def _update_visualization(self):
        """Update the network visualization with drone icons and labels below"""
        self.ax.clear()

        if not self.nodes:
            return

        # Draw edges first (underneath nodes)
        nx.draw_networkx_edges(
            self.network_graph,
            self.node_positions,
            edge_color="gray",
            alpha=0.3,
            width=0.5,
        )

        # Draw nodes with drone icons and labels
        for node_id in self.network_graph.nodes():
            pos = self.node_positions[node_id]
            is_master = node_id == self.master_node

            # Draw the icon
            if self.leader_img is not None and self.follower_img is not None:
                img = self.leader_img if is_master else self.follower_img
                imagebox = OffsetImage(img, zoom=0.15)
                ab = AnnotationBbox(imagebox, pos, frameon=False, pad=0)
                self.ax.add_artist(ab)
            else:
                # Fallback to circles if images aren't available
                node_color = "red" if is_master else "lightblue"
                nx.draw_networkx_nodes(
                    self.network_graph,
                    {node_id: pos},
                    nodelist=[node_id],
                    node_color=node_color,
                    node_size=1500,  # Make all nodes the same size
                )

            # Add label below the icon
            label_text = f"{self.nodes[node_id].address}\n(ID: {node_id})"
            label_y_offset = -0.15  # Adjust this value to move labels up or down
            self.ax.text(
                pos[0],
                pos[1] + label_y_offset,
                label_text,
                horizontalalignment="center",
                verticalalignment="top",
                fontsize=8,
            )

        # Set visualization properties
        self.ax.set_title("Drone Network Topology", pad=20, fontsize=14)
        self.ax.set_xlim(0, 2)
        self.ax.set_ylim(0, 2)
        self.canvas.draw()

        # Update status information
        self._update_status_info()

    def _update_status_info(self):
        """Update status labels and node list"""
        # Update master info
        master_node = next(
            (node for node in self.nodes.values() if node.is_master), None
        )
        if master_node:
            self.master_label.setText(
                f"Master: {master_node.address} (ID: {master_node.id})"
            )
        else:
            self.master_label.setText("Master: Not Selected")

        # Update active nodes count
        self.active_nodes_label.setText(f"Active Nodes: {len(self.nodes)}")

        # Update nodes list
        nodes_text = ""
        for node in sorted(self.nodes.values(), key=lambda x: x.port):
            status = "Master" if node.is_master else "Slave"
            nodes_text += f"{node.address} (ID: {node.id}, {status})\n"
        self.nodes_list.setText(nodes_text)

    def _kill_master_node(self):
        """Handler for Kill Master Node button"""
        if self.nodes:
            master_node = next(
                (node for node in self.nodes.values() if node.is_master), None
            )
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
            was_master = node.is_master
            
            # Remove from data structures first
            self.nodes.pop(node_id)
            self.network_graph.remove_node(node_id)

            # Stop the node after removing from data structures
            node._cleanup_in_progress = True  # Prevent signal emission
            node.stop()

            # Handle master election if needed
            if was_master and self.nodes:
                remaining_ids = list(self.nodes.keys())
                if remaining_ids:
                    new_master_id = max(remaining_ids)
                    self.master_node = new_master_id
                    for remaining_node in self.nodes.values():
                        remaining_node.is_master = (remaining_node.id == new_master_id)

            # Recalculate node positions after removing a node
            self.node_positions = self._calculate_node_positions()
            self._update_visualization()

    def _restore_network(self):
        """Handler for Restore Network button"""
        self._setup_network()
        self.statusBar.showMessage("Network restored")

    # Add these new methods to handle network events:
    def _handle_master_change(self, new_master_id):
        """Handle master node change events"""
        self.master_node = new_master_id
        for node in self.nodes.values():
            node.is_master = (node.id == new_master_id)
        self._update_visualization()

    def _handle_node_death(self, node_id):
        """Handle node death events"""
        if node_id in self.nodes and not self.nodes[node_id]._cleanup_in_progress:
            self._kill_node(node_id)
    
    def closeEvent(self, event):
        """Handle application close event"""
        # Safely stop all nodes
        nodes_to_stop = list(self.nodes.values())
        for node in nodes_to_stop:
            if hasattr(node, "stop"):
                node._cleanup_in_progress = True
                node.stop()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = NetworkVisualizerWindow("network_config.json")
    window.show()
    sys.exit(app.exec_())
