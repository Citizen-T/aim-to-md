import unittest
from datetime import datetime
from src.aim_parser import Message
from src.markdown_converter import MarkdownConverter


class TestMarkdownConverter(unittest.TestCase):
    def setUp(self):
        self.converter = MarkdownConverter()
        
    def test_convert_single_message(self):
        messages = [
            Message(sender="UserA", timestamp="10:56:59 PM", content="hello")
        ]
        
        markdown = self.converter.convert(messages)
        
        expected = "**UserA** (10:56:59 PM):\n> hello\n"
        self.assertEqual(markdown, expected)
    
    def test_convert_multiple_messages(self):
        messages = [
            Message(sender="UserA", timestamp="10:56:59 PM", content="hello"),
            Message(sender="UserB", timestamp="10:57:05 PM", content="hi there")
        ]
        
        markdown = self.converter.convert(messages)
        
        expected = """**UserA** (10:56:59 PM):
> hello

**UserB** (10:57:05 PM):
> hi there
"""
        self.assertEqual(markdown, expected)
    
    def test_convert_with_system_message(self):
        messages = [
            Message(sender="UserA", timestamp="10:56:59 PM", content="hello"),
            Message(sender="System", timestamp="", content="UserA signed off at 12:28:30 AM", is_system_message=True)
        ]
        
        markdown = self.converter.convert(messages)
        
        expected = """**UserA** (10:56:59 PM):
> hello

> [!NOTE]
> UserA signed off at 12:28:30 AM
"""
        self.assertEqual(markdown, expected)
    
    def test_convert_with_markdown_special_chars(self):
        messages = [
            Message(sender="User", timestamp="11:00:00 AM", content="This has *asterisks* and _underscores_")
        ]
        
        markdown = self.converter.convert(messages)
        
        expected = "**User** (11:00:00 AM):\n> This has \\*asterisks\\* and \\_underscores\\_\n"
        self.assertEqual(markdown, expected)
    
    def test_convert_multiline_message(self):
        messages = [
            Message(sender="User", timestamp="11:00:00 AM", content="Line one\nLine two\nLine three")
        ]
        
        markdown = self.converter.convert(messages)
        
        expected = """**User** (11:00:00 AM):
> Line one
> Line two
> Line three
"""
        self.assertEqual(markdown, expected)
    
    def test_add_header_with_date(self):
        messages = [
            Message(sender="UserA", timestamp="10:56:59 PM", content="hello")
        ]
        date = datetime(2004, 5, 18)
        
        markdown = self.converter.convert(messages, conversation_date=date)
        
        expected = """---
date: 2004-05-18
tags:
  - aim
---

# AIM Conversation - May 18, 2004

**UserA** (10:56:59 PM):
> hello
"""
        self.assertEqual(markdown, expected)
    
    def test_consecutive_messages_same_sender_within_threshold(self):
        # Messages within 2 minutes should be grouped together
        messages = [
            Message(sender="UserA", timestamp="10:56:59 PM", content="hello"),
            Message(sender="UserA", timestamp="10:57:30 PM", content="how are you doing?"),
            Message(sender="UserA", timestamp="10:58:15 PM", content="are you still there?")
        ]
        
        markdown = self.converter.convert(messages)
        
        expected = """**UserA** (10:56:59 PM):
> hello
> how are you doing?
> are you still there?
"""
        self.assertEqual(markdown, expected)
    
    def test_consecutive_messages_same_sender_beyond_threshold(self):
        # Messages more than 2 minutes apart should start new groups
        messages = [
            Message(sender="UserA", timestamp="10:56:59 PM", content="hello"),
            Message(sender="UserA", timestamp="10:59:30 PM", content="guess you fell asleep")
        ]
        
        markdown = self.converter.convert(messages)
        
        expected = """**UserA** (10:56:59 PM):
> hello

**UserA** (10:59:30 PM):
> guess you fell asleep
"""
        self.assertEqual(markdown, expected)
    
    def test_mixed_grouping_scenario(self):
        # Test complex scenario with different senders and time gaps
        messages = [
            Message(sender="Alice", timestamp="10:56:59 PM", content="Hey"),
            Message(sender="Alice", timestamp="10:57:01 PM", content="How's it going?"),
            Message(sender="Bob", timestamp="10:57:05 PM", content="Hi there!"),
            Message(sender="Alice", timestamp="11:00:22 PM", content="Guess you fell asleep")
        ]
        
        markdown = self.converter.convert(messages)
        
        expected = """**Alice** (10:56:59 PM):
> Hey
> How's it going?

**Bob** (10:57:05 PM):
> Hi there\\!

**Alice** (11:00:22 PM):
> Guess you fell asleep
"""
        self.assertEqual(markdown, expected)
    
    def test_convert_auto_response_message(self):
        # Test auto response formatting as QUOTE callout
        messages = [
            Message(sender="Bob", timestamp="1:04:11 AM", content="sleeping", is_system_message=True, is_auto_response=True)
        ]
        
        markdown = self.converter.convert(messages)
        
        expected = """> [!QUOTE] Auto response from Bob (1:04:11 AM)
> sleeping
"""
        self.assertEqual(markdown, expected)
    
    def test_convert_auto_response_multiline(self):
        # Test auto response with multiline content
        messages = [
            Message(sender="Alice", timestamp="2:30:15 PM", content="Out for lunch\nBack in 1 hour", is_system_message=True, is_auto_response=True)
        ]
        
        markdown = self.converter.convert(messages)
        
        expected = """> [!QUOTE] Auto response from Alice (2:30:15 PM)
> Out for lunch
> Back in 1 hour
"""
        self.assertEqual(markdown, expected)
    
    def test_convert_mixed_regular_auto_response_and_system(self):
        # Test conversation with regular messages, auto responses, and system messages
        messages = [
            Message(sender="Bob", timestamp="1:04:10 AM", content="Hey there"),
            Message(sender="Alice", timestamp="1:04:11 AM", content="sleeping", is_system_message=True, is_auto_response=True),
            Message(sender="System", timestamp="", content="Alice signed off at 1:05:00 AM", is_system_message=True),
            Message(sender="Bob", timestamp="1:04:15 AM", content="Talk tomorrow then")
        ]
        
        markdown = self.converter.convert(messages)
        
        expected = """**Bob** (1:04:10 AM):
> Hey there

> [!QUOTE] Auto response from Alice (1:04:11 AM)
> sleeping

> [!NOTE]
> Alice signed off at 1:05:00 AM

**Bob** (1:04:15 AM):
> Talk tomorrow then
"""
        self.assertEqual(markdown, expected)
    
    def test_convert_auto_response_with_special_chars(self):
        # Test auto response with markdown special characters
        messages = [
            Message(sender="Bob", timestamp="3:15:45 PM", content="*busy* with _work_!", is_system_message=True, is_auto_response=True)
        ]
        
        markdown = self.converter.convert(messages)
        
        expected = """> [!QUOTE] Auto response from Bob (3:15:45 PM)
> \\*busy\\* with \\_work\\_\\!
"""
        self.assertEqual(markdown, expected)
    
    def test_convert_session_concluded_message(self):
        # Test session concluded formatting as ATTENTION callout
        messages = [
            Message(sender="System", timestamp="", content="Session concluded at 9:52:55 PM", is_system_message=True, is_session_concluded=True)
        ]
        
        markdown = self.converter.convert(messages)
        
        expected = """> [!ATTENTION]
> Session concluded at 9:52:55 PM
"""
        self.assertEqual(markdown, expected)
    
    def test_convert_mixed_system_messages(self):
        # Test conversation with regular, auto response, session concluded, and system messages
        messages = [
            Message(sender="Bob", timestamp="9:51:32 PM", content="bye love"),
            Message(sender="Alice", timestamp="9:51:35 PM", content="sleeping", is_system_message=True, is_auto_response=True),
            Message(sender="System", timestamp="", content="Alice signed off at 9:51:43 PM", is_system_message=True),
            Message(sender="System", timestamp="", content="Session concluded at 9:52:55 PM", is_system_message=True, is_session_concluded=True)
        ]
        
        markdown = self.converter.convert(messages)
        
        expected = """**Bob** (9:51:32 PM):
> bye love

> [!QUOTE] Auto response from Alice (9:51:35 PM)
> sleeping

> [!NOTE]
> Alice signed off at 9:51:43 PM

> [!ATTENTION]
> Session concluded at 9:52:55 PM
"""
        self.assertEqual(markdown, expected)
    
    def test_convert_multiple_session_concluded_messages(self):
        # Test conversation with multiple session concluded messages
        messages = [
            Message(sender="Alice", timestamp="10:00:00 PM", content="hello"),
            Message(sender="System", timestamp="", content="Session concluded at 10:30:00 PM", is_system_message=True, is_session_concluded=True),
            Message(sender="Bob", timestamp="11:00:00 PM", content="hi again"),
            Message(sender="System", timestamp="", content="Session concluded at 11:45:00 PM", is_system_message=True, is_session_concluded=True)
        ]
        
        markdown = self.converter.convert(messages)
        
        expected = """**Alice** (10:00:00 PM):
> hello

> [!ATTENTION]
> Session concluded at 10:30:00 PM

**Bob** (11:00:00 PM):
> hi again

> [!ATTENTION]
> Session concluded at 11:45:00 PM
"""
        self.assertEqual(markdown, expected)
    
    def test_frontmatter_with_description(self):
        """Test that description is included in frontmatter when provided"""
        messages = [
            Message(sender="Alice", timestamp="10:56:59 PM", content="Hello"),
            Message(sender="Bob", timestamp="10:57:05 PM", content="Hi there")
        ]
        
        date = datetime(2004, 5, 18)
        description = "In this conversation Alice and Bob exchange greetings and discuss their plans for the weekend."
        
        result = self.converter.convert(messages, conversation_date=date, description=description)
        
        expected_frontmatter = """---
date: 2004-05-18
description: In this conversation Alice and Bob exchange greetings and discuss their plans for the weekend.
tags:
  - aim
---"""
        
        self.assertIn(expected_frontmatter, result)
        self.assertIn("# AIM Conversation - May 18, 2004", result)
    
    def test_frontmatter_without_description(self):
        """Test that frontmatter works without description (backward compatibility)"""
        messages = [
            Message(sender="Alice", timestamp="10:56:59 PM", content="Hello")
        ]
        
        date = datetime(2004, 5, 18)
        
        result = self.converter.convert(messages, conversation_date=date)
        
        expected_frontmatter = """---
date: 2004-05-18
tags:
  - aim
---"""
        
        self.assertIn(expected_frontmatter, result)
        # Should not contain 'description:' line
        self.assertNotIn("description:", result)
        # Should contain tags
        self.assertIn("tags:", result)
    
    def test_no_frontmatter_without_date(self):
        """Test that no frontmatter is generated when no date is provided, even with description"""
        messages = [
            Message(sender="Alice", timestamp="10:56:59 PM", content="Hello")
        ]
        
        description = "Alice greets someone in this brief conversation."
        
        result = self.converter.convert(messages, description=description)
        
        # Should not contain frontmatter at all
        self.assertNotIn("---", result)
        self.assertNotIn("description:", result)
        self.assertNotIn("date:", result)
    
    def test_frontmatter_with_default_tags(self):
        """Test that default aim tag is included when no custom tags provided"""
        messages = [
            Message(sender="Alice", timestamp="10:56:59 PM", content="Hello")
        ]
        
        date = datetime(2004, 5, 18)
        
        result = self.converter.convert(messages, conversation_date=date)
        
        expected_frontmatter = """---
date: 2004-05-18
tags:
  - aim
---"""
        
        self.assertIn(expected_frontmatter, result)
    
    def test_frontmatter_with_custom_tags(self):
        """Test that custom tags are included when provided"""
        messages = [
            Message(sender="Alice", timestamp="10:56:59 PM", content="Hello"),
            Message(sender="Bob", timestamp="10:57:05 PM", content="Hi there")
        ]
        
        date = datetime(2004, 5, 18)
        custom_tags = ["aim", "friends", "casual-chat"]
        
        result = self.converter.convert(messages, conversation_date=date, tags=custom_tags)
        
        expected_frontmatter = """---
date: 2004-05-18
tags:
  - aim
  - friends
  - casual-chat
---"""
        
        self.assertIn(expected_frontmatter, result)
    
    def test_frontmatter_with_description_and_tags(self):
        """Test frontmatter with both description and tags"""
        messages = [
            Message(sender="Alice", timestamp="10:56:59 PM", content="Hello"),
            Message(sender="Bob", timestamp="10:57:05 PM", content="Hi there")
        ]
        
        date = datetime(2004, 5, 18)
        description = "Alice and Bob exchange greetings in this conversation."
        custom_tags = ["aim", "greetings"]
        
        result = self.converter.convert(messages, conversation_date=date, description=description, tags=custom_tags)
        
        expected_frontmatter = """---
date: 2004-05-18
description: Alice and Bob exchange greetings in this conversation.
tags:
  - aim
  - greetings
---"""
        
        self.assertIn(expected_frontmatter, result)
    
    def test_frontmatter_with_empty_tags_list(self):
        """Test that empty tags list results in default tag"""
        messages = [
            Message(sender="Alice", timestamp="10:56:59 PM", content="Hello")
        ]
        
        date = datetime(2004, 5, 18)
        empty_tags = []
        
        result = self.converter.convert(messages, conversation_date=date, tags=empty_tags)
        
        # Empty list should be treated as None and get default tag
        expected_frontmatter = """---
date: 2004-05-18
tags:
  - aim
---"""
        
        self.assertIn(expected_frontmatter, result)
    
    def test_frontmatter_with_single_custom_tag(self):
        """Test frontmatter with single custom tag"""
        messages = [
            Message(sender="Alice", timestamp="10:56:59 PM", content="Hello")
        ]
        
        date = datetime(2004, 5, 18)
        single_tag = ["work-chat"]
        
        result = self.converter.convert(messages, conversation_date=date, tags=single_tag)
        
        expected_frontmatter = """---
date: 2004-05-18
tags:
  - work-chat
---"""
        
        self.assertIn(expected_frontmatter, result)


if __name__ == '__main__':
    unittest.main()