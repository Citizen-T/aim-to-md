import unittest
import os
from pathlib import Path
from src.aim_parser import AIMParser
from src.markdown_converter import MarkdownConverter


class TestIntegration(unittest.TestCase):
    def setUp(self):
        self.parser = AIMParser()
        self.converter = MarkdownConverter()
        self.test_dir = Path(__file__).parent
        self.sample_file = self.test_dir / "fixtures" / "sample-conversation.htm"
    
    def test_full_conversion_pipeline(self):
        # Read the sample file
        with open(self.sample_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Parse the HTML
        messages = self.parser.parse(html_content)
        
        # Verify we got messages
        self.assertGreater(len(messages), 0)
        
        # Use a mock date since our test fixture doesn't have a date in the filename
        from datetime import datetime
        date = datetime(2023, 3, 15)
        
        # Convert to Markdown
        markdown = self.converter.convert(messages, conversation_date=date)
        
        # Basic validation - check that it has proper structure
        self.assertIn("# AIM Conversation - March 15, 2023", markdown)
        # Check that we have the expected users and messages
        self.assertIn("**Alice**", markdown)
        self.assertIn("**Bob**", markdown)
        self.assertIn("> hey there\\!", markdown)  # Exclamation mark gets escaped
        self.assertIn("> oh hi Alice", markdown)
        
        # Check that the last message is the sign off
        self.assertIn("*[System: Alice signed off at 7:39:25 PM]*", markdown)
    
    def test_messages_have_expected_content(self):
        with open(self.sample_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        messages = self.parser.parse(html_content)
        
        # Check basic structure without revealing personal information
        self.assertGreater(len(messages), 2)  # Should have multiple messages
        
        # Check that we have both regular messages and system messages
        regular_messages = [m for m in messages if not m.is_system_message]
        system_messages = [m for m in messages if m.is_system_message]
        
        self.assertGreater(len(regular_messages), 0)
        self.assertGreater(len(system_messages), 0)
        
        # Check that messages have proper structure
        for msg in regular_messages[:5]:  # Check first 5 messages
            self.assertIsNotNone(msg.sender)
            self.assertIsNotNone(msg.timestamp)
            self.assertIsNotNone(msg.content)
            self.assertGreater(len(msg.sender.strip()), 0)
            self.assertGreater(len(msg.content.strip()), 0)
        
        # Check for specific test cases we included
        # 1. Messages with quotes
        quote_messages = [m for m in regular_messages if '"' in m.content]
        self.assertGreater(len(quote_messages), 0)
        
        # 2. Multiline messages (content that spans multiple lines in HTML)
        # Our fixture includes "the website redesign we talked about\nlast week"
        multiline_messages = [m for m in regular_messages if 'website redesign' in m.content]
        self.assertGreater(len(multiline_messages), 0)
        
        # 3. Messages that look like they're from another user (GameMaster42: ...)
        game_messages = [m for m in regular_messages if 'GameMaster42:' in m.content]
        self.assertGreater(len(game_messages), 0)
        
        # Check for sign off message
        last_message = messages[-1]
        self.assertTrue(last_message.is_system_message)
        self.assertIn("signed off", last_message.content)


if __name__ == '__main__':
    unittest.main()