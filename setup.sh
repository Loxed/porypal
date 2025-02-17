#!/bin/bash

# Define the virtual environment directory
VENV_DIR="venv"

# Step 1: Create a virtual environment
python3 -m venv $VENV_DIR

# Step 2: Determine the path to the Python interpreter in the virtual environment
PYTHON_BIN="$VENV_DIR/bin/python"

# Step 3: Activate the virtual environment
source $VENV_DIR/bin/activate

# Step 4: Install requirements.txt if it exists
REQUIREMENTS_FILE="requirements.txt"

if [[ -f "$REQUIREMENTS_FILE" ]]; then
    if pip install -r "$REQUIREMENTS_FILE"; then
        echo "Requirements installed successfully."
    else
        echo "Failed to install requirements from $REQUIREMENTS_FILE."
        exit 1
    fi
else
    echo "No requirements.txt file found."
fi

echo "Virtual environment created, activated, and requirements installed."
echo "You can now run your script using the Python interpreter in the virtual environment."
echo "To deactivate the virtual environment, run: deactivate"