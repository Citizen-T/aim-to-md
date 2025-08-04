# AIM to Markdown Converter

A Python utility to convert old AOL Instant Messenger (AIM) conversation logs from HTML format to clean, readable Markdown files.

## Features

- Parses AIM HTML conversation logs exported from the AOL Instant Messenger client
- Converts messages to well-formatted Markdown
- Preserves timestamps and sender information
- Handles system messages (e.g., "user signed off")
- Escapes special Markdown characters to prevent formatting issues
- Supports batch processing of multiple files
- Intelligently groups consecutive messages from the same sender (within 2-minute intervals)
- Extracts conversation dates from filenames
- **AI-powered intelligent filename generation** using Google's Gemini AI
- Generates descriptive filenames in standardized format: `YYYY-MM-DD Title [participants]`

## Installation

1. Clone this repository:
```bash
git clone https://github.com/Citizen-T/aim-to-md.git
cd aim-to-md
```

2. Create a virtual environment (optional but recommended):
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Setup

### Google AI API Key

This tool uses Google's Gemini AI to generate intelligent conversation titles. You'll need to:

1. Get a Google AI API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Set it as an environment variable:

```bash
export GEMINI_API_KEY="your-api-key-here"
```

Or on Windows:
```cmd
set GEMINI_API_KEY=your-api-key-here
```

**Note**: The API key is required when no output filename is specified (using the `-o` option). The tool will generate intelligent filenames using AI when this key is provided.

## Usage

### Basic Usage

Convert a single AIM HTML file to Markdown:

```bash
python aim2md.py "path/to/conversation.htm"
```

When no output filename is specified, the tool automatically generates an intelligent filename using AI in the format:
```
YYYY-MM-DD Title [user1, user2].md
```

Examples:
- `2025-08-04 Planning first trip to beach [Alice, Bob].md`
- `2021-02-20 Birthday wishes for Alice [Alice, Bob].md`
- `2020-09-22 Catching up during COVID lockdown [Alice, Bob].md`

### Specify Output Location

```bash
python aim2md.py "conversation.htm" -o "output.md"
```

### Process Multiple Files

Convert all HTML files in a directory:

```bash
python aim2md.py "path/to/aim-logs/"
```

Process directories recursively:

```bash
python aim2md.py "path/to/aim-logs/" -r
```

## Example Output

Input HTML:
```html
<B><FONT COLOR="#0000ff">Alice<!-- (10:57:26 PM)--></B></FONT>: <FONT>Hey</FONT><BR>
<B><FONT COLOR="#0000ff">Alice<!-- (10:57:28 PM)--></B></FONT>: <FONT>How's it going?</FONT><BR>
<B><FONT COLOR="#0000ff">Alice<!-- (11:00:22 PM)--></B></FONT>: <FONT>Guess you fell asleep</FONT><BR>
<!-- System message -->
Alice signed off at 11:15:30 PM
```

Output Markdown:
```markdown
# AIM Conversation - May 18, 2004

**Alice** (10:57:26 PM):
> Hey
> How's it going?

**Alice** (11:00:22 PM):
> Guess you fell asleep

> [!NOTE]
> Alice signed off at 11:15:30 PM
```

The converter intelligently groups messages from the same sender when they occur within 2 minutes of each other, showing only the first timestamp. Messages separated by longer gaps start new groups. System messages (like sign-offs) are displayed as callout blocks to distinguish them from regular messages.

## Running Tests

Run all tests:
```bash
python -m pytest
```

Run with coverage:
```bash
python -m pytest -v
```

## Project Structure

```
aim-to-md/
├── src/
│   ├── __init__.py
│   ├── aim_parser.py      # HTML parsing logic
│   ├── markdown_converter.py  # Markdown conversion logic
│   └── main.py            # CLI application
├── tests/
│   ├── fixtures/
│   │   └── sample-conversation.htm  # Sample AIM conversation for testing
│   ├── test_aim_parser.py
│   ├── test_markdown_converter.py
│   └── test_integration.py
├── aim2md.py              # Entry point script
└── README.md
```

## License

This project is open source and available under the MIT License.