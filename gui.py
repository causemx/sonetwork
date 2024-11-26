import sys
import math
import random
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QPushButton, QLabel, QGraphicsView,
                           QGraphicsScene, QStatusBar)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter
import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import numpy as np
from network import Node  # Import from previous example

class NetworkVisualizerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Self-Organizing Network Visualizer")
        self.setGeometry(100, 100, 1200, 800)

        # Initialize network
        self.nodes = []
        self.network_graph = nx.Graph()
        self.master_node = 0

        # Calculate static node positions
        self.node_positions = self._calculate_node_positions()

        # Create main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)

        # Create control panel
        control_panel = self._create_control_panel()
        layout.addWidget(control_panel)

        # Create network visualization
        self.figure, self.ax = plt.subplots(figsize=(8, 6))
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas, stretch=2)

        # Initialize status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

        # Setup network
        self._setup_network()

        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_visualization)
        self.update_timer.start(1000)  # Update every second

    def _calculate_node_positions(self):
        """Calculate static positions for nodes in a circle"""
        positions = {}
        num_nodes = 10
        radius = 0.8  # Radius of the circle
        center = (1.0, 1.0)  # Center of the circle

        for i in range(num_nodes):
            # Calculate angle for this node (in radians)
            angle = 2 * math.pi * i / num_nodes
            # Calculate position (x, y)
            x = center[0] + radius * math.cos(angle)
            y = center[1] + radius * math.sin(angle)
            positions[i] = (x, y)

        return positions

    def _create_control_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        panel.setMinimumWidth(200)  # Set minimum width for control panel

        # Network status
        status_group = QWidget()
        status_layout = QVBoxLayout(status_group)

        # Title
        title_label = QLabel("Network Status")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        status_layout.addWidget(title_label)

        self.master_label = QLabel("Master Node: 0")
        self.active_nodes_label = QLabel("Active Nodes: 10")
        status_layout.addWidget(self.master_label)
        status_layout.addWidget(self.active_nodes_label)
        layout.addWidget(status_group)

        # Control buttons
        buttons_group = QWidget()
        buttons_layout = QVBoxLayout(buttons_group)

        # Title
        controls_label = QLabel("Controls")
        controls_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        buttons_layout.addWidget(controls_label)

        # Style for buttons
        button_style = """
            QPushButton {
                background-color: #f0f0f0;
                border: 2px solid #c0c0c0;
                border-radius: 5px;
                padding: 5px;
                margin: 2px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
        """

        kill_master_btn = QPushButton("Kill Master Node")
        kill_master_btn.setStyleSheet(button_style)
        kill_master_btn.clicked.connect(self._kill_master_node)

        kill_random_btn = QPushButton("Kill Random Node")
        kill_random_btn.setStyleSheet(button_style)
        kill_random_btn.clicked.connect(self._kill_random_node)

        restore_btn = QPushButton("Restore Network")
        restore_btn.setStyleSheet(button_style)
        restore_btn.clicked.connect(self._restore_network)

        buttons_layout.addWidget(kill_master_btn)
        buttons_layout.addWidget(kill_random_btn)
        buttons_layout.addWidget(restore_btn)
        layout.addWidget(buttons_group)

        # Add legend
        legend_group = QWidget()
        legend_layout = QVBoxLayout(legend_group)

        legend_label = QLabel("Legend")
        legend_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        legend_layout.addWidget(legend_label)

        master_legend = QLabel("● Red - Master Node")
        master_legend.setStyleSheet("color: red;")
        slave_legend = QLabel("● Blue - Slave Node")
        slave_legend.setStyleSheet("color: blue;")

        legend_layout.addWidget(master_legend)
        legend_layout.addWidget(slave_legend)
        layout.addWidget(legend_group)

        # Add stretch to push everything to the top
        layout.addStretch()

        return panel

    def _setup_network(self):
        # Create nodes
        for i in range(10):
            node = Node(i)
            node.start()
            self.nodes.append(node)
            self.network_graph.add_node(i)

        # Create edges (fully connected network)
        for i in range(10):
            for j in range(i + 1, 10):
                self.network_graph.add_edge(i, j)

        self._update_visualization()

    def _update_visualization(self):
        self.ax.clear()

        # Draw nodes
        node_colors = []
        node_sizes = []
        for node in self.network_graph.nodes():
            if node == self.master_node:
                node_colors.append('red')
                node_sizes.append(700)  # Larger size for master
            else:
                node_colors.append('lightblue')
                node_sizes.append(500)  # Normal size for slaves

        # Draw nodes with static positions
        nx.draw_networkx_nodes(self.network_graph,
                             self.node_positions,
                             node_color=node_colors,
                             node_size=node_sizes)

        # Draw edges
        nx.draw_networkx_edges(self.network_graph,
                             self.node_positions,
                             edge_color='gray',
                             alpha=0.5)

        # Draw labels
        labels = {node: f"Node {node}" for node in self.network_graph.nodes()}
        nx.draw_networkx_labels(self.network_graph,
                              self.node_positions,
                              labels,
                              font_size=8)

        self.ax.set_title("Network Topology")
        # Set fixed axis limits
        self.ax.set_xlim(0, 2)
        self.ax.set_ylim(0, 2)
        self.canvas.draw()

        # Update status labels
        self.master_label.setText(f"Master Node: {self.master_node}")
        self.active_nodes_label.setText(f"Active Nodes: {len(self.nodes)}")

    def _kill_master_node(self):
        if self.nodes:
            master_node = next(node for node in self.nodes if node.is_master)
            self._kill_node(master_node.id)
            self.statusBar.showMessage(f"Killed master node {master_node.id}")

    def _kill_random_node(self):
        if self.nodes:
            node_to_kill = random.choice(self.nodes)
            self._kill_node(node_to_kill.id)
            self.statusBar.showMessage(f"Killed node {node_to_kill.id}")

    def _kill_node(self, node_id):
        node = next((n for n in self.nodes if n.id == node_id), None)
        if node:
            node.stop()
            self.nodes.remove(node)
            self.network_graph.remove_node(node_id)

            if node.is_master:
                remaining_ids = [n.id for n in self.nodes]
                if remaining_ids:
                    new_master_id = max(remaining_ids)
                    self.master_node = new_master_id
                    for n in self.nodes:
                        if n.id == new_master_id:
                            n.is_master = True
                        else:
                            n.is_master = False

    def _restore_network(self):
        for node in self.nodes:
            node.stop()

        self.nodes.clear()
        self.network_graph.clear()

        self._setup_network()
        self.statusBar.showMessage("Network restored")

    def closeEvent(self, event):
        for node in self.nodes:
            node.stop()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = NetworkVisualizerWindow()
    window.show()
    sys.exit(app.exec_())
