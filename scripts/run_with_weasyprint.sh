#!/bin/bash
# Helper script to run Python with WeasyPrint support on macOS
# This sets the required library path for GTK/GObject libraries

export DYLD_LIBRARY_PATH="/opt/homebrew/lib:$DYLD_LIBRARY_PATH"

# Run the command passed as arguments
exec "$@"

# Made with Bob
