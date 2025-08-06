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
- **YAML frontmatter support** with AI-generated descriptions and automatic tagging for Obsidian and other markdown tools
- **Configurable custom tagging system** - define your own tags with descriptions and let AI automatically apply them to conversations

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
2. Copy the `.env-template` file to `.env`:
   ```bash
   cp .env-template .env
   ```
3. Edit the `.env` file and replace `your-api-key-here` with your actual API key:
   ```
   GEMINI_API_KEY=your-actual-api-key-here
   ```

**Note**: The API key is required when no output filename is specified (using the `-o` option). The tool will generate intelligent filenames using AI when this key is provided.

## Usage

### Basic Usage

Convert a single AIM HTML file to Markdown:

```bash
python -m src.main "path/to/conversation.htm"
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
python -m src.main "conversation.htm" -o "output.md"
```

### Process Multiple Files

Convert all HTML files in a directory:

```bash
python -m src.main "path/to/aim-logs/"
```

Process directories recursively:

```bash
python -m src.main "path/to/aim-logs/" -r
```

### Custom Tagging

The tool automatically looks for a `config.yaml` file in your current directory. If found, it will use your custom tag configurations to automatically categorize conversations:

```bash
python -m src.main "conversation.htm"
```

You can also specify a custom configuration file location:

```bash
python -m src.main "conversation.htm" -t "path/to/custom-config.yaml"
```

This will apply your custom tags in addition to the default `aim` tag based on conversation content.

## Custom Tag Configuration

You can define custom tags to automatically categorize your conversations based on their content. Create a `config.yaml` file in your working directory (or specify a custom path with `-t`) that defines tag names and descriptions:

```yaml
tags:
  - name: homework-help
    description: >
      This conversation contains a discussion of homework where one of the participants is assisting the other
      in completing an assignment.
  - name: sports
    description: >
      This conversation contains a discussion of sports (e.g. baseball, basketball, football, etc.) whether
      professional or otherwise.
  - name: gaming
    description: >
      This conversation contains discussions about video games, gaming platforms, or playing games together.
```

When you run the converter with a `config.yaml` file present (or specify a custom config with `-t`), the AI will analyze each conversation and automatically apply matching tags. For example, a conversation that contains both homework help and sports discussion would receive both tags:

```markdown
---
date: 2025-08-05
description: In this chat, Alice helps Bob work through some chemistry homework and then the two discuss the upcoming homecoming football game.
tags:
  - aim
  - homework-help
  - sports
---
```

**Benefits:**
- **Automatic categorization**: Let AI analyze and categorize your conversations
- **Consistent tagging**: Standardize how conversations are tagged across your collection
- **Enhanced searchability**: Use tags to quickly find conversations about specific topics
- **Obsidian integration**: Tags work seamlessly with Obsidian's tag system for organization and filtering

You can create your own configuration file with any tags that make sense for your conversation collection.

## Participant Mapping

In addition to custom tags, you can configure participant mappings to link conversations to specific people in your note-taking system. This creates markdown links in the frontmatter and uses human-readable names in AI-generated descriptions.

### Configuration

Add a `participants` section to your `config.yaml` file:

```yaml
tags:
  - name: homework-help
    description: This conversation contains homework discussion
  - name: gaming
    description: This conversation contains discussions about video games

participants:
  - name: Bob
    aim: bob123
    md: "[[Bob Smith]]"
  - name: Alice
    aim: alice456
    md: "[[Alice Sanders]]" 
  - name: Charlie
    aim: charlie789
    md: "[[Charlie Brown]]"
```

**Configuration Fields:**
- `name`: Human-readable short name (first name or nickname)
- `aim`: The exact AIM username/handle as it appears in conversation logs
- `md`: Markdown link format for your note-taking system (typically `[[Full Name]]`)

### Benefits

**Markdown Links in Frontmatter:**
```markdown
---
date: 2025-08-05
participants:
  - [[Bob Smith]]
  - [[Alice Sanders]]
description: In this conversation Bob and Alice discuss their weekend plans and upcoming project deadlines.
tags:
  - aim
  - homework-help
---
```

**Human-Readable AI Descriptions:**
Instead of: _"In this conversation bob123 asks alice456 for help with homework"_  
You get: _"In this conversation Bob asks Alice for help with homework"_

**Automatic Fallback:**
If a participant isn't configured, the tool automatically falls back to using their AIM handle, ensuring no conversation data is lost.

### Obsidian Integration

This feature works seamlessly with Obsidian's linking system:
- `[[Bob Smith]]` creates automatic links to person notes
- Use Obsidian's graph view to visualize conversation networks
- Filter conversations by participant using the frontmatter
- Build comprehensive personal knowledge bases with conversation history

## YAML Frontmatter Support

The converter automatically includes YAML frontmatter when a date can be extracted from the filename. The frontmatter includes a `tags` property with the default `aim` tag, and when using intelligent filename generation (no `-o` option specified), it also includes an AI-generated description and participant information. This is particularly useful for Obsidian and other markdown tools that support frontmatter:

**With intelligent filename generation and participant mapping (default behavior):**
```markdown
---
date: 2004-05-18
participants:
  - [[Alice Sanders]]
  - [[Bob Smith]]
description: In this conversation Alice and Bob catch up on recent events, discuss their weekend plans, and share updates about their work projects.
tags:
  - aim
---

# AIM Conversation - May 18, 2004

**Alice** (10:57:26 PM):
> Hey there!
```

**With manual output filename (using `-o` option):**
```markdown
---
date: 2004-05-18
tags:
  - aim
---

# AIM Conversation - May 18, 2004

**Alice** (10:57:26 PM):
> Hey there!
```

Files without extractable dates will not include frontmatter:

```markdown
**Alice** (10:57:26 PM):
> Hey there!
```

The AI-generated description summarizes the main topics and themes of the conversation, making it easier for other LLMs and tools to understand the content without reading the entire conversation. This feature only activates when using intelligent filename generation, which requires a `GEMINI_API_KEY`.

**Frontmatter Properties:**
All generated markdown files include comprehensive frontmatter with:
- `date`: Conversation date extracted from filename
- `participants`: List of participant links (when configured) or AIM handles  
- `description`: AI-generated conversation summary using human-readable names
- `tags`: Default `aim` tag plus any custom tags that match the conversation content

This provides rich metadata for note-taking systems like Obsidian, enabling powerful organization, linking, and search capabilities across your conversation collection.

## Example Output

Input HTML:
```html
<B><FONT COLOR="#0000ff">Alice<!-- (10:57:26 PM)--></B></FONT>: <FONT>Hey</FONT><BR>
<B><FONT COLOR="#0000ff">Alice<!-- (10:57:28 PM)--></B></FONT>: <FONT>How's it going?</FONT><BR>
<B><FONT COLOR="#0000ff">Alice<!-- (11:00:22 PM)--></B></FONT>: <FONT>Guess you fell asleep</FONT><BR>
<!-- System message -->
Alice signed off at 11:15:30 PM
```

Output Markdown (with intelligent filename generation):
```markdown
---
date: 2004-05-18
description: Alice attempts to start a conversation but receives no response, eventually realizing the other person may have fallen asleep before signing off.
tags:
  - aim
---

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
│   ├── filename_generator.py  # AI-powered filename and description generation
│   ├── tag_evaluator.py   # Custom tag evaluation system
│   └── main.py            # CLI application
├── tests/
│   ├── fixtures/
│   │   └── sample-conversation.htm  # Sample AIM conversation for testing
│   ├── test_aim_parser.py
│   ├── test_markdown_converter.py
│   ├── test_filename_generator.py
│   ├── test_tag_evaluator.py
│   ├── test_integration.py
│   └── test_integration_tagging.py
├── aim2md.py              # Entry point script
└── README.md
```

## License

This project is open source and available under the MIT License.