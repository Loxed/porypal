# <span style="float: left; margin-right: 10px;"><img src="gui/porypal.ico" width="128" height="128"></span> Porypal


Porypal is a specialized image processing tool designed for Pokémon Gen 3 ROM hacking and decompilation projects (pokeemerald/pokefirered). It automates sprite and tileset conversion while maintaining strict adherence to the Pokémon Gen 3's 16-color palette specifications.

<br>
<br>
<br>

## Key Features

  - Automatically convert every pixel from an input image to its closest color in a JASC-PAL file.
  - Multi-palette preview interface for comparison and cherry-picking.
  - Prioritizes conversions that maintain the highest number of distinct colors (up to 16)
  - Configurable tileset transformation pipeline via YAML

![Porypal UI](docs/img/ui.png)


> **_Implementation Note_**: The default configuration targets conversion of 4x4 NPC overworld tilesets from modern Pokémon titles ([DiegoWT and UltimoSpriter's "Gen 5 Characters in Gen 4 OW style 2.0"](https://web.archive.org/web/20231001155146/https://reliccastle.com/resources/370/), [VanillaSunshine's "Gen 4 Characters (HGSS/DPPt)"](https://eeveeexpo.com/resources/404/)) to Gen 3 format (`graphics/object_events/pics/people`). The pipeline can be reconfigured for other asset conversion workflows in the [configuration](config.yaml) file.

## Installation

### Prerequisites
Ensure you have Python 3.6+ installed on your system. You can download Python from the [official website](https://www.python.org/downloads/).

### 1. Clone the repository or download the code
Download the repository to your local machine or clone it using Git:


```bash
git clone https://github.com/Loxed/porypal.git
```
**Note**: _I recommend cloning the project inside your pokefirered/pokeemerald's `tools` folder._

### 2. Install dependencies

#### Windows
1. Open Command Prompt (`cmd`) or PowerShell.
2. Navigate to the project directory:

   ```bash
   cd \path\to\decomp\tools\porypal
   ```

3. Install the required dependencies using `pip`:

   ```bash
   pip install -r requirements.txt
   ```

#### macOS / Linux
1. Open Terminal.
2. Navigate to the project directory:

   ```bash
   cd /path/to/decomp/tools/porypal
   ```

3. Run the installer:
    ```bash
    ./setup.sh
    ```

### 3. Run the application

After installing the dependencies, you can run the `main.py` script.

   ```bash
   python3 main.py
   ```

### 4. Build from source

To build the program, use the following command:

#### Windows

```bash
pyinstaller --onefile --windowed --hidden-import encodings --add-data "palettes;palettes" --icon="gui/porypal.ico" --add-data="gui/porypal.ico;." .\main.py

# Copy additional resources
cp config.yaml dist/config.yaml
cp -r gui dist/gui
cp -r palettes dist/palettes
cp -r docs dist/docs
cp -r example dist/example
```

### MacOS

#### Silicon

## Directory Structure

```
porypal/
├── controller/        # Controller components (MVC pattern)
├── model/            # Model components (MVC pattern)
├── view/             # View components (MVC pattern)
├── gui/              # GUI assets and resources
│   ├── porypal.ico   # Application icon
│   └── porypalette.ui # Qt UI definition file
├── example/          # Example files and reference images
├── palettes/         # JASC-PAL color definitions
├── docs/             # Documentation and guides
├── build/            # Build output directory
├── .venv/            # Python virtual environment
├── config.yaml       # Pipeline configuration
├── main.py           # Core application logic
├── main.spec         # PyInstaller specification file
├── requirements.txt  # Python dependencies
├── setup.sh          # Unix installation script
└── LICENSE           # MIT License file
```

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact
For questions or support, reach out to `prison_lox` on Discord.

## Credits

The way the config is currently setup is specifically to import and convert these overworld sprites:

- [Gen 5 Characters in Gen 4 OW style 2.0](https://web.archive.org/web/20231001155146/https://reliccastle.com/resources/370/) by DiegoWT and UltimoSpriter
- [ALL Official Gen 4 Overworld Sprites v1.5](https://eeveeexpo.com/resources/404/) by VanillaSunshine
