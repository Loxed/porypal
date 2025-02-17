import sys
import os
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QFileDialog,
                            QVBoxLayout, QHBoxLayout, QGridLayout, QGraphicsScene, 
                            QGraphicsView, QLabel, QSizePolicy, QGroupBox)
from PyQt5.QtGui import QColor, QFont, QPainter, QPen, QPixmap, QImage
from PyQt5.QtCore import Qt, QSize, QEvent
from PIL import Image

import yaml

def set_dark_theme(app):
    app.setStyle("Fusion")
    palette = app.palette()
    dark = QColor(45, 45, 45)
    text = QColor(220, 220, 220)
    highlight = QColor(10, 32, 55)
    
    palette.setColor(palette.Window, dark)
    palette.setColor(palette.WindowText, text)
    palette.setColor(palette.Base, QColor(30, 30, 30))
    palette.setColor(palette.AlternateBase, dark)
    palette.setColor(palette.ToolTipBase, dark)
    palette.setColor(palette.ToolTipText, text)
    palette.setColor(palette.Text, text)
    palette.setColor(palette.Button, dark)
    palette.setColor(palette.ButtonText, text)
    palette.setColor(palette.Highlight, highlight)
    palette.setColor(palette.HighlightedText, Qt.white)
    app.setPalette(palette)

def set_light_theme(app):
    app.setStyle("Fusion")
    palette = app.palette()
    light = QColor(240, 240, 240)
    text = QColor(0, 0, 0)
    highlight = QColor(10, 32, 55)
    
    palette.setColor(palette.Window, light)
    palette.setColor(palette.WindowText, text)
    palette.setColor(palette.Base, QColor(255, 255, 255))
    palette.setColor(palette.AlternateBase, light)
    palette.setColor(palette.ToolTipBase, light)
    palette.setColor(palette.ToolTipText, text)
    palette.setColor(palette.Text, text)
    palette.setColor(palette.Button, light)
    palette.setColor(palette.ButtonText, text)
    palette.setColor(palette.Highlight, highlight)
    palette.setColor(palette.HighlightedText, Qt.white)
    app.setPalette(palette)

def color_distance(c1, c2):
    return (c1.red() - c2.red())**2 + (c1.green() - c2.green())**2 + (c1.blue() - c2.blue())**2

class PoryPalettes(QWidget):
    def __init__(self):
        super().__init__()
        self.palettes = []
        self.num_palettes = sum(f.endswith('.pal') for f in os.listdir('palettes') if os.path.exists('palettes')) if config['palettes']['more_colors'] else 4
        self.target_image = QImage()
        self.converted_data = []
        self.best_indices = []
        self.selected_index = 0
        self.current_file_path = ""

        self.load_config()

        self.initUI()
        self.load_palettes()

    def load_config(self):
        with open('config.yaml', 'r') as file:
            self.config = yaml.safe_load(file)
    
    def initUI(self):
        self.setWindowTitle("PoryPalettes - Image Processor")
        self.setMinimumSize(1600, 900)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # Top controls
        control_layout = QHBoxLayout()
        
        # Image Processing Group
        processing_group = QGroupBox("Image Processing")
        processing_layout = QHBoxLayout()
        
        self.btn_tileset = QPushButton("⚙️ Load Overworld Tileset")
        self.btn_target = QPushButton("🎨 Load Target Sprite")
        self.btn_save = QPushButton("💾 Save Selected")
        self.btn_toggle_theme = QPushButton("💡")
        
        for btn in [self.btn_tileset, self.btn_target, self.btn_save, self.btn_toggle_theme]:
            btn.setFixedHeight(40)
            btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        
        self.btn_tileset.clicked.connect(self.load_tileset)
        self.btn_target.clicked.connect(self.load_target_image)
        self.btn_save.clicked.connect(self.save_converted_image)
        self.btn_toggle_theme.clicked.connect(self.toggle_theme)
        
        processing_layout.addWidget(self.btn_tileset)
        processing_layout.addWidget(self.btn_target)
        processing_layout.addWidget(self.btn_save)
        processing_layout.addWidget(self.btn_toggle_theme)
        processing_group.setLayout(processing_layout)
        
        control_layout.addWidget(processing_group)
        main_layout.addLayout(control_layout)
        
        # Main content
        content_layout = QVBoxLayout()
        
        # Original preview
        original_box = QVBoxLayout()
        original_box.addWidget(QLabel("Original Sprite"))
        self.original_scene = QGraphicsScene()
        self.original_view = QGraphicsView()
        self.original_view.setScene(self.original_scene)
        self.original_view.setRenderHints(QPainter.Antialiasing)
        original_box.addWidget(self.original_view)
        content_layout.addLayout(original_box, 30)
        
        # Converted previews
        converted_box = QGridLayout()
        converted_box.addWidget(QLabel("Click to select conversion (Green = Selected, Blue = Most Diverse)"), 0, 0, 1, 4)
        converted_box.setHorizontalSpacing(15)
        
        self.result_views = []
        self.result_scenes = []
        self.result_labels = []
        for i in range(self.num_palettes):
            scene = QGraphicsScene()
            view = QGraphicsView()
            view.setScene(scene)
            view.setRenderHints(QPainter.Antialiasing)
            view.installEventFilter(self)
            label = QLabel("Loading...")
            label.setAlignment(Qt.AlignCenter)
            
            converted_box.addWidget(label, 1+i, 1)
            converted_box.addWidget(view, 1+i, 2)
            self.result_views.append(view)
            self.result_scenes.append(scene)
            self.result_labels.append(label)
        
        content_layout.addLayout(converted_box, 70)
        main_layout.addLayout(content_layout)
        self.setLayout(main_layout)
    
    def toggle_theme(self):
        """Switch between light and dark theme"""
        if self.palette().color(self.palette().Window) == QColor(45, 45, 45):
            set_light_theme(QApplication.instance())
            self.btn_toggle_theme.setText("🌙")
            self.config['dark_mode'] = 'light'
            with open('config.yaml', 'w') as file:
                yaml.dump(self.config, file, default_flow_style=False)
        else:
            set_dark_theme(QApplication.instance())
            self.btn_toggle_theme.setText("💡")
            self.config['dark_mode'] = 'dark'
            with open('config.yaml', 'w') as file:
                yaml.dump(self.config, file, default_flow_style=False)


    def load_tileset(self):
        """Load and process tileset image using only PyQt5"""
        # Read from config.yaml
        tileset_config = self.config['tileset']
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Tileset Image", "", 
            "Images (*.png *.jpg *.jpeg *.bmp *.gif)")
        
        if not file_path:
            return

        try:
            # Load image with QPixmap
            pixmap = QPixmap(file_path)
            if pixmap.isNull():
                raise ValueError("Failed to load image")

            # Handle different tile sizes based on config
            matched_size = None
            for size in tileset_config['supported_sizes']:
                if pixmap.width() == size['width'] and pixmap.height() == size['height']:
                    matched_size = size
                    break
            
            if matched_size:
                if matched_size['resize_to'] != pixmap.width():
                    pixmap = pixmap.scaled(matched_size['resize_to'], matched_size['resize_to'], 
                                        Qt.IgnoreAspectRatio, Qt.FastTransformation)
            elif tileset_config['resize_tileset']:
                pixmap = pixmap.scaled(tileset_config['resize_to'], tileset_config['resize_to'],
                                    Qt.IgnoreAspectRatio, Qt.FastTransformation)

            # Extract 32x32 sprites based on the sprite size defined in config
            sprites = []
            for y in range(0, pixmap.height(), tileset_config['sprite_size']):
                for x in range(0, pixmap.width(), tileset_config['sprite_size']):
                    sprite = pixmap.copy(x, y, tileset_config['sprite_size'], tileset_config['sprite_size'])
                    if not sprite.isNull():
                        sprites.append(sprite)

            # Define sprite order (using config)
            ORDER = tileset_config['sprite_order']
            
            # Create output image based on the output width/height in config
            output = QImage(self.config['output']['output_width'], self.config['output']['output_height'], QImage.Format_ARGB32)
            output.fill(Qt.transparent)
            
            # Paint sprites in order
            painter = QPainter(output)
            for i, idx in enumerate(ORDER):
                if idx < len(sprites):
                    painter.drawPixmap(i * tileset_config['sprite_size'], 0, sprites[idx])
            painter.end()

            # Update application state
            self.current_file_path = file_path
            self.target_image = output

            # Update preview
            self.original_scene.clear()
            pixmap = QPixmap.fromImage(self.target_image)
            self.original_scene.addPixmap(pixmap)
            self.original_view.fitInView(self.original_scene.itemsBoundingRect(), Qt.KeepAspectRatio)
            
            self.convert_all()
            print("Tileset processed successfully")

        except Exception as e:
            print(f"Tileset error: {str(e)}")

    def eventFilter(self, source, event):
        if event.type() == QEvent.MouseButtonPress:
            if source in self.result_views:
                index = self.result_views.index(source)
                self.handle_selection(index)
                return True
        return super().eventFilter(source, event)

    def handle_selection(self, index):
        self.selected_index = index
        self.update_highlights()

    def update_highlights(self):
        for i, view in enumerate(self.result_views):
            styles = []
            if i == self.selected_index:
                styles.append("border: 3px solid #4CAF50;")  # Green for selection
            elif i in self.best_indices:
                styles.append("border: 2px solid #2196F3;")  # Blue for diversity
            view.setStyleSheet("".join(styles))

    def load_palettes(self):
        palette_dir = os.path.join(os.path.dirname(__file__), "palettes")
        if not os.path.exists(palette_dir):
            print(f"Missing palettes directory: {palette_dir}")
            return

        self.palettes = []
        more_colors = self.config.get('palettes', {}).get('more_colors', False)
        npc_priority = self.config.get('palettes', {}).get('npc_priority', False)

        for filename in sorted(os.listdir(palette_dir)):
            if not filename.endswith(".pal"):
                continue

            # If more_colors is False and npc_priority is True, only load the 4 NPC palettes
            if not more_colors and npc_priority and filename not in {"npc_1.pal", "npc_2.pal", "npc_3.pal", "npc_4.pal"}:
                continue
            
            try:
                with open(os.path.join(palette_dir, filename), 'r') as f:
                    lines = [line.strip() for line in f.readlines()]

                # Validate the palette file format
                if len(lines) < 3 or lines[0] != "JASC-PAL" or lines[1] != "0100":
                    continue

                color_count = int(lines[2])
                colors = [QColor(*map(int, line.split())) for line in lines[3:3+color_count]]

                # Add the palette to the list
                self.palettes.append({
                    'name': filename[:-4],  # Remove .pal extension
                    'colors': colors,
                    'transparent': colors[0] if colors else QColor(0, 0, 0)
                })

            except Exception as e:
                print(f"Error loading palette {filename}: {e}")

        # Update labels for the loaded palettes
        for i, palette in enumerate(self.palettes[:self.num_palettes]):
            self.result_labels[i].setText(palette['name'])


    def load_target_image(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Target Sprite", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif)", options=options)
        
        if not file_path:
            return
        
        self.current_file_path = file_path
        self.target_image = QImage(file_path)
        if self.target_image.isNull():
            return
        
        self.original_scene.clear()
        pixmap = QPixmap.fromImage(self.target_image)
        self.original_scene.addPixmap(pixmap)
        self.original_view.fitInView(self.original_scene.itemsBoundingRect(), Qt.KeepAspectRatio)
        
        self.convert_all()

    def convert_all(self):
        if not self.palettes or self.target_image.isNull():
            return
        
        self.converted_data = []
        max_colors = -1
        self.best_indices = []
        
        for i, palette in enumerate(self.palettes[:self.num_palettes]):
            converted, used_colors = self.convert_image(palette)
            self.converted_data.append(converted)
            
            self.result_labels[i].setText(
                f"{palette['name']}\n({used_colors} colors used)"
            )
            
            if used_colors > max_colors:
                max_colors = used_colors
                self.best_indices = [i]
            elif used_colors == max_colors:
                self.best_indices.append(i)
            
            pixmap = QPixmap.fromImage(converted)
            self.result_scenes[i].clear()
            self.result_scenes[i].addPixmap(pixmap)
            self.result_views[i].fitInView(
                self.result_scenes[i].itemsBoundingRect(), Qt.KeepAspectRatio
            )
        
        self.selected_index = self.best_indices[0] if self.best_indices else 0
        self.update_highlights()

    def convert_image(self, palette):
        width = self.target_image.width()
        height = self.target_image.height()
        converted = QImage(width, height, QImage.Format_RGB32)
        transparent_color = palette['transparent']
        available_colors = palette['colors'][1:] if len(palette['colors']) > 1 else []
        used_colors = set()
        
        for y in range(height):
            for x in range(width):
                pixel_color = self.target_image.pixelColor(x, y)
                
                if pixel_color.alpha() < 255:
                    converted_color = transparent_color
                else:
                    if available_colors:
                        closest = min(available_colors, 
                                    key=lambda c: color_distance(pixel_color, c))
                        converted_color = closest
                    else:
                        converted_color = pixel_color
                
                converted.setPixelColor(x, y, converted_color)
                used_colors.add((
                    converted_color.red(),
                    converted_color.green(),
                    converted_color.blue()
                ))
        
        return converted, len(used_colors)

    def save_converted_image(self):
        if not self.converted_data or not self.current_file_path:
            return
        
        try:
            selected_idx = self.selected_index
            selected_palette = self.palettes[selected_idx]
            output_path = self.generate_output_path(selected_palette['name'])
            
            # Convert QImage to index array
            qimage = self.converted_data[selected_idx]
            width = qimage.width()
            height = qimage.height()
            
            # Create palette mapping
            palette_colors = selected_palette['colors']
            palette_order = [(c.red(), c.green(), c.blue()) for c in palette_colors]
            color_to_index = {rgb: idx for idx, rgb in enumerate(palette_order)}
            
            # Build index data
            indices = []
            for y in range(height):
                for x in range(width):
                    color = qimage.pixelColor(x, y)
                    rgb = (color.red(), color.green(), color.blue())
                    indices.append(color_to_index[rgb])
            
            # Create and save 4-bit PNG
            with Image.new("P", (width, height)) as im:
                # Build palette data
                palette_data = []
                for color in palette_colors:
                    palette_data += [color.red(), color.green(), color.blue()]
                # Pad to 256 colors (768 entries)
                palette_data += [0] * (768 - len(palette_data))
                im.putpalette(palette_data)
                
                # Set transparency and pixel data
                im.info["transparency"] = 0
                im.putdata(indices)
                
                # Save directly with overwrite
                im.save(output_path, format="PNG", bits=4, optimize=True)
            
            print(f"Successfully saved to: {output_path}")

        except Exception as e:
            print(f"Save failed: {str(e)}")

    def generate_output_path(self, palette_name):
        base_dir = os.path.dirname(self.current_file_path)
        base_name = os.path.splitext(os.path.basename(self.current_file_path))[0]
        return os.path.join(base_dir, f"{base_name}_{palette_name}.png")

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # check config for theme
    with open('config.yaml', 'r') as file:
        config = yaml.safe_load(file)

    set_dark_theme(app) if config['dark_mode'] == 'dark' else set_light_theme(app)

    window = PoryPalettes()
    window.show()
    sys.exit(app.exec_())