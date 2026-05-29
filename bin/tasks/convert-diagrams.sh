#!/bin/bash
# Script to convert Mermaid diagram files (.mmd) to SVG format

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check if mmdc is available
if ! command -v mmdc > /dev/null 2>&1; then
    echo "Error: mmdc (mermaid-cli) not found in PATH" >&2
    echo "Please ensure you're running this script in a nix-shell environment" >&2
    echo "Run: nix-shell" >&2
    exit 1
fi

# Check if any files were provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <file1.mmd> [file2.mmd] ..." >&2
    echo "Converts Mermaid diagram files (.mmd) to SVG format" >&2
    exit 1
fi

# Process each .mmd file
for mmd_file in "$@"; do
    # Check if file exists
    if [ ! -f "$mmd_file" ]; then
        echo "Warning: File not found: $mmd_file" >&2
        continue
    fi
    
    # Check if file has .mmd extension
    if [[ ! "$mmd_file" =~ \.mmd$ ]]; then
        echo "Warning: File does not have .mmd extension: $mmd_file" >&2
        continue
    fi
    
    # Generate output filename (replace .mmd with .svg)
    svg_file="${mmd_file%.mmd}.svg"
    
    echo "Converting: $mmd_file -> $svg_file"
    
    # Convert using mmdc
    mmdc -i "$mmd_file" -o "$svg_file"
    
    if [ $? -eq 0 ]; then
        echo "  ✓ Successfully created $svg_file"
    else
        echo "  ✗ Failed to convert $mmd_file" >&2
        exit 1
    fi
done

echo ""
echo "Conversion complete!"

