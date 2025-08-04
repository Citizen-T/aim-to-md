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

*[System: UserA signed off at 12:28:30 AM]*
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
        
        expected = """# AIM Conversation - May 18, 2004

**UserA** (10:56:59 PM):
> hello
"""
        self.assertEqual(markdown, expected)
    
    def test_consecutive_messages_same_sender(self):
        messages = [
            Message(sender="UserA", timestamp="10:56:59 PM", content="hello"),
            Message(sender="UserA", timestamp="10:57:10 PM", content="how are you doing?"),
            Message(sender="UserA", timestamp="10:57:15 PM", content="are you still there?")
        ]
        
        markdown = self.converter.convert(messages)
        
        expected = """**UserA** (10:56:59 PM):
> hello

(10:57:10 PM):
> how are you doing?

(10:57:15 PM):
> are you still there?
"""
        self.assertEqual(markdown, expected)


if __name__ == '__main__':
    unittest.main()