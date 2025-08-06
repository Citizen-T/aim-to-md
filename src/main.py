#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path
from typing import List, Tuple

from src.aim_parser import AIMParser
from src.markdown_converter import MarkdownConverter
from src.filename_generator import FilenameGenerator
from src.tag_evaluator import TagEvaluator


def process_file(input_path: Path, output_path: Path, description: str = None, custom_tags: List[str] = None, participants: List[str] = None) -> None:
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
        
        # Prepare final tags (combine default aim tag with custom tags)
        final_tags = ["aim"]
        if custom_tags:
            final_tags.extend(custom_tags)
        
        # Convert to Markdown
        markdown = converter.convert(messages, conversation_date=date, group_consecutive=True, description=description, tags=final_tags, participants=participants)
        
        # Write the output
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown)
        
        print(f"Successfully converted {input_path.name} → {output_path.name}")
        print(f"  - Parsed {len(messages)} messages")
        
    except Exception as e:
        print(f"Error processing {input_path}: {e}", file=sys.stderr)
        raise


def _generate_standardized_filename(input_file: Path, tag_evaluator: TagEvaluator = None) -> Tuple[Path, str, List[str], List[str]]:
    """Generate a standardized filename, description, tags, and participants using LLM"""
    parser = AIMParser()
    filename_generator = FilenameGenerator()
    
    # Read and parse the file to extract messages and date
    with open(input_file, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    messages = parser.parse(html_content)
    
    # Extract date from filename
    try:
        date = parser.extract_date_from_filename(input_file.name)
    except ValueError:
        date = None
    
    # Extract participants from messages
    participants_set = set()
    for message in messages:
        if not message.is_system_message and message.sender:
            participants_set.add(message.sender)
    
    # Generate name mapping for human-readable names if tag evaluator is provided
    name_mapping = None
    if tag_evaluator:
        name_mapping = tag_evaluator.get_human_readable_names(list(participants_set))
    
    # Generate standardized filename and description using LLM
    standardized_name = filename_generator.generate_filename(messages, date, name_mapping)
    description = filename_generator.generate_description(messages, name_mapping)
    
    # Evaluate custom tags and map participants if tag evaluator is provided
    custom_tags = []
    mapped_participants = []
    if tag_evaluator:
        custom_tags = tag_evaluator.evaluate_tags(messages)
        mapped_participants = tag_evaluator.map_participants(list(participants_set))
    else:
        # If no tag evaluator, fall back to raw AIM handles
        mapped_participants = list(participants_set)
    
    return input_file.parent / f"{standardized_name}.md", description, custom_tags, mapped_participants


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
    
    parser.add_argument(
        "-t", "--tags-config",
        help="Path to YAML configuration file (default: looks for config.yaml in current directory)"
    )
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    
    # Initialize tag evaluator - check for config file
    tag_evaluator = None
    config_path = None
    
    if args.tags_config:
        # User specified a custom config file
        config_path = Path(args.tags_config)
    else:
        # Check for default config.yaml in current directory
        default_config = Path("config.yaml")
        if default_config.exists():
            config_path = default_config
    
    if config_path:
        if not config_path.exists():
            print(f"Error: Configuration file '{config_path}' does not exist", file=sys.stderr)
            sys.exit(1)
        try:
            tag_evaluator = TagEvaluator(config_path)
            if tag_evaluator.tag_configs:
                print(f"Loaded {len(tag_evaluator.tag_configs)} custom tag(s) from {config_path}")
        except Exception as e:
            print(f"Error loading configuration: {e}", file=sys.stderr)
            sys.exit(1)
    
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
        # Initialize description, custom_tags, and participants variables
        description = None
        custom_tags = None
        participants = None
        
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
            # Generate standardized filename, description, custom tags, and participants using LLM
            output_file, description, custom_tags, participants = _generate_standardized_filename(input_file, tag_evaluator)
        
        # If we have a tag evaluator but haven't evaluated tags yet (e.g., when using -o option)
        if tag_evaluator and (custom_tags is None or participants is None):
            # Need to parse the file to evaluate tags and participants
            aim_parser = AIMParser()
            with open(input_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            messages = aim_parser.parse(html_content)
            
            if custom_tags is None:
                custom_tags = tag_evaluator.evaluate_tags(messages)
            
            if participants is None:
                # Extract participants and map them
                participants_set = set()
                for message in messages:
                    if not message.is_system_message and message.sender:
                        participants_set.add(message.sender)
                participants = tag_evaluator.map_participants(list(participants_set))
        
        try:
            process_file(input_file, output_file, description, custom_tags, participants)
        except Exception:
            # Error already printed in process_file
            continue
    
    print(f"\nProcessed {len(files_to_process)} file(s)")


if __name__ == "__main__":
    main()