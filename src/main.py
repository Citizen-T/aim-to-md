#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path
from typing import List

from src.aim_parser import AIMParser
from src.markdown_converter import MarkdownConverter


def process_file(input_path: Path, output_path: Path) -> None:
    """Process a single AIM HTML file and convert it to Markdown."""
    parser = AIMParser()
    converter = MarkdownConverter()
    
    try:
        # Read the HTML file
        with open(input_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Parse the messages
        messages = parser.parse(html_content)
        if not messages:
            print(f"Warning: No messages found in {input_path}")
            return
        
        # Extract date from filename
        try:
            date = parser.extract_date_from_filename(input_path.name)
        except ValueError:
            date = None
        
        # Convert to Markdown
        markdown = converter.convert(messages, conversation_date=date, group_consecutive=True)
        
        # Write the output
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown)
        
        print(f"Successfully converted {input_path.name} → {output_path.name}")
        print(f"  - Parsed {len(messages)} messages")
        
    except Exception as e:
        print(f"Error processing {input_path}: {e}", file=sys.stderr)
        raise


def main():
    parser = argparse.ArgumentParser(
        description="Convert AOL Instant Messenger (AIM) conversation logs to Markdown format"
    )
    
    parser.add_argument(
        "input",
        help="Input HTML file or directory containing AIM conversation logs"
    )
    
    parser.add_argument(
        "-o", "--output",
        help="Output file or directory for Markdown files (default: same location with .md extension)"
    )
    
    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        help="Process directories recursively"
    )
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    
    if not input_path.exists():
        print(f"Error: Input path '{input_path}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    # Determine files to process
    files_to_process: List[Path] = []
    
    if input_path.is_file():
        if not input_path.suffix.lower() in ['.htm', '.html']:
            print(f"Error: Input file must be an HTML file (.htm or .html)", file=sys.stderr)
            sys.exit(1)
        files_to_process = [input_path]
    else:
        # Directory processing
        pattern = "**/*.htm*" if args.recursive else "*.htm*"
        files_to_process = list(input_path.glob(pattern))
        
        if not files_to_process:
            print(f"No HTML files found in {input_path}", file=sys.stderr)
            sys.exit(1)
    
    # Process each file
    for input_file in files_to_process:
        # Determine output path
        if args.output:
            output_path = Path(args.output)
            if len(files_to_process) > 1:
                # Multiple files - output should be a directory
                if not output_path.exists():
                    output_path.mkdir(parents=True, exist_ok=True)
                output_file = output_path / input_file.with_suffix('.md').name
            else:
                # Single file
                output_file = output_path
        else:
            # Default: same location with .md extension
            output_file = input_file.with_suffix('.md')
        
        try:
            process_file(input_file, output_file)
        except Exception:
            # Error already printed in process_file
            continue
    
    print(f"\nProcessed {len(files_to_process)} file(s)")


if __name__ == "__main__":
    main()