# view/automation_view.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog
from PyQt5.QtCore import Qt
import os

class AutomationView(QWidget):
    """
    View for the automation feature that allows users to select input folder,
    preset file, output folder, and return to the tileset editor.
    """
    
    def __init__(self, controller):
        super().__init__()
        
        self.controller = controller
        
        # Set window properties
        self.setWindowTitle("PoryPal - Automation")
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint)
        self.setMinimumWidth(400)
        self.setMinimumHeight(250)
        
        # Create layout
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(15)
        self.layout.setContentsMargins(20, 20, 20, 20)
        
        # Add title
        self.title_label = QLabel("Automation")
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.title_label)
        
        # Add description
        self.description_label = QLabel("Apply a preset to multiple images in a folder")
        self.description_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.description_label)
        
        # Add status label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.status_label)
        
        # Add buttons
        self.btn_input_folder = QPushButton("📁 Select Input Folder")
        self.btn_input_folder.setMinimumSize(136, 40)
        self.btn_input_folder.clicked.connect(self.select_input_folder)
        self.layout.addWidget(self.btn_input_folder)
        
        self.btn_preset = QPushButton("📋 Select Preset")
        self.btn_preset.setMinimumSize(136, 40)
        self.btn_preset.clicked.connect(self.select_preset)
        self.layout.addWidget(self.btn_preset)
        
        self.btn_output_folder = QPushButton("📂 Select Output Folder")
        self.btn_output_folder.setMinimumSize(136, 40)
        self.btn_output_folder.clicked.connect(self.select_output_folder)
        self.layout.addWidget(self.btn_output_folder)
        
        self.btn_start = QPushButton("▶️ Start Automation")
        self.btn_start.setMinimumSize(136, 40)
        self.btn_start.clicked.connect(self.start_automation)
        self.btn_start.setEnabled(False)
        self.layout.addWidget(self.btn_start)
        
        self.btn_return = QPushButton("↩️ Return to Tileset Editor")
        self.btn_return.setMinimumSize(136, 40)
        self.btn_return.clicked.connect(self.return_to_editor)
        self.layout.addWidget(self.btn_return)
        
        # Add stretch to push everything to the top
        self.layout.addStretch()
        
        # Initialize state
        self.input_folder = ""
        self.preset_file = ""
        self.output_folder = ""
        
        # Update status
        self.update_status()
    
    def select_input_folder(self):
        """Open dialog to select input folder."""
        folder = QFileDialog.getExistingDirectory(
            self, "Select Input Folder with Images", ""
        )
        
        if folder:
            self.input_folder = folder
            self.update_status()
    
    def select_preset(self):
        """Open dialog to select preset file."""
        preset_folder = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "presets")
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Preset File", preset_folder, "JSON Files (*.json)"
        )
        
        if file_path:
            self.preset_file = file_path
            self.update_status()
    
    def select_output_folder(self):
        """Open dialog to select output folder."""
        folder = QFileDialog.getExistingDirectory(
            self, "Select Output Folder", ""
        )
        
        if folder:
            self.output_folder = folder
            self.update_status()
    
    def update_status(self):
        """Update the status label and enable/disable the start button."""
        status_parts = []
        
        if self.input_folder:
            status_parts.append(f"Input: {os.path.basename(self.input_folder)}")
        else:
            status_parts.append("Input: Not selected")
            
        if self.preset_file:
            status_parts.append(f"Preset: {os.path.basename(self.preset_file)}")
        else:
            status_parts.append("Preset: Not selected")
            
        if self.output_folder:
            status_parts.append(f"Output: {os.path.basename(self.output_folder)}")
        else:
            status_parts.append("Output: Not selected")
            
        self.status_label.setText(" | ".join(status_parts))
        
        # Enable start button only if all selections are made
        self.btn_start.setEnabled(
            bool(self.input_folder) and 
            bool(self.preset_file) and 
            bool(self.output_folder)
        )
    
    def start_automation(self):
        """Start the automation process."""
        self.controller.start_automation(
            self.input_folder,
            self.preset_file,
            self.output_folder
        )
    
    def return_to_editor(self):
        """Return to the tileset editor."""
        self.controller.return_to_editor() 