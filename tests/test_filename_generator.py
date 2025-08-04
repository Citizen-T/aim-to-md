import unittest
import os
from unittest.mock import patch, MagicMock
from datetime import datetime
from src.aim_parser import Message
from src.filename_generator import FilenameGenerator


class TestFilenameGenerator(unittest.TestCase):
    def setUp(self):
        # Mock the API key environment variable
        self.api_key_patcher = patch.dict(os.environ, {'GEMINI_API_KEY': 'fake-api-key'})
        self.api_key_patcher.start()
        
        # Mock the Gemini API
        self.genai_patcher = patch('src.filename_generator.genai')
        self.mock_genai = self.genai_patcher.start()
        
        # Mock the model and response
        self.mock_model = MagicMock()
        self.mock_genai.GenerativeModel.return_value = self.mock_model
        
        self.generator = FilenameGenerator()
    
    def tearDown(self):
        self.api_key_patcher.stop()
        self.genai_patcher.stop()
    
    def test_init_without_api_key(self):
        """Test that FilenameGenerator raises error when API key is missing"""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError) as cm:
                FilenameGenerator()
            self.assertIn("GEMINI_API_KEY environment variable is required", str(cm.exception))
    
    def test_extract_participants(self):
        """Test participant extraction from messages"""
        messages = [
            Message(sender="Alice", timestamp="10:56:59 PM", content="hello"),
            Message(sender="Bob", timestamp="10:57:05 PM", content="hi there"),
            Message(sender="Alice", timestamp="10:57:10 PM", content="how are you?"),
            Message(sender="System", timestamp="", content="Bob signed off", is_system_message=True)
        ]
        
        participants = self.generator._extract_participants(messages)
        
        # Should only include non-system message senders
        self.assertEqual(participants, {"Alice", "Bob"})
    
    def test_sanitize_title(self):
        """Test title sanitization for filename compatibility"""
        test_cases = [
            ("Normal title", "Normal title"),
            ("Title with / slash", "Title with slash"),
            ("Title: with colon", "Title with colon"),
            ("Title<>with|brackets", "Title with brackets"),
            ("Multiple   spaces", "Multiple spaces"),
            ("  Leading and trailing  ", "Leading and trailing")
        ]
        
        for input_title, expected in test_cases:
            with self.subTest(input=input_title):
                result = self.generator._sanitize_title(input_title)
                self.assertEqual(result, expected)
    
    @patch('src.filename_generator.genai')
    def test_generate_title_with_llm_success(self, mock_genai):
        """Test successful title generation with LLM"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.text = "Birthday celebration planning"
        self.mock_model.generate_content.return_value = mock_response
        
        messages = [
            Message(sender="Alice", timestamp="10:56:59 PM", content="Happy birthday Bob!"),
            Message(sender="Bob", timestamp="10:57:05 PM", content="Thank you!")
        ]
        
        title = self.generator._generate_title_with_llm(messages)
        
        self.assertEqual(title, "Birthday celebration planning")
        self.mock_model.generate_content.assert_called_once()
    
    @patch('src.filename_generator.genai')
    def test_generate_title_with_llm_api_error(self, mock_genai):
        """Test handling of LLM API errors"""
        # Setup mock to raise an exception
        self.mock_model.generate_content.side_effect = Exception("API Error")
        
        messages = [
            Message(sender="Alice", timestamp="10:56:59 PM", content="Hello"),
            Message(sender="Bob", timestamp="10:57:05 PM", content="Hi")
        ]
        
        with self.assertRaises(RuntimeError) as cm:
            self.generator._generate_title_with_llm(messages)
        
        self.assertIn("Failed to generate title using Gemini API", str(cm.exception))
    
    def test_generate_title_empty_messages(self):
        """Test title generation with empty message list"""
        title = self.generator._generate_title_with_llm([])
        self.assertEqual(title, "Conversation")
    
    def test_generate_filename_with_date(self):
        """Test complete filename generation with provided date"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.text = "Planning beach trip"
        self.mock_model.generate_content.return_value = mock_response
        
        messages = [
            Message(sender="Alice", timestamp="10:56:59 PM", content="Let's go to the beach"),
            Message(sender="Bob", timestamp="10:57:05 PM", content="Sounds great!")
        ]
        date = datetime(2025, 8, 4)
        
        filename = self.generator.generate_filename(messages, date)
        
        expected = "2025-08-04 Planning beach trip [Alice, Bob]"
        self.assertEqual(filename, expected)
    
    def test_generate_filename_without_date(self):
        """Test filename generation using current date when no date provided"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.text = "General conversation"
        self.mock_model.generate_content.return_value = mock_response
        
        messages = [
            Message(sender="Alice", timestamp="10:56:59 PM", content="Hey there"),
            Message(sender="Bob", timestamp="10:57:05 PM", content="Hi Alice")
        ]
        
        filename = self.generator.generate_filename(messages)
        
        # Should use current date
        current_year = datetime.now().year
        self.assertIn(str(current_year), filename)
        self.assertIn("General conversation", filename)
        self.assertIn("[Alice, Bob]", filename)
    
    def test_generate_filename_with_quoted_title(self):
        """Test handling of LLM response with quotes"""
        # Setup mock response with quotes
        mock_response = MagicMock()
        mock_response.text = '"Weekend planning session"'
        self.mock_model.generate_content.return_value = mock_response
        
        messages = [
            Message(sender="Alice", timestamp="10:56:59 PM", content="What should we do this weekend?"),
            Message(sender="Bob", timestamp="10:57:05 PM", content="Let's make some plans")
        ]
        date = datetime(2025, 8, 4)
        
        filename = self.generator.generate_filename(messages, date)
        
        # Quotes should be removed
        expected = "2025-08-04 Weekend planning session [Alice, Bob]"
        self.assertEqual(filename, expected)
    
    def test_generate_filename_long_title_truncation(self):
        """Test that very long titles are truncated"""
        # Setup mock response with very long title
        mock_response = MagicMock()
        mock_response.text = "This is a very long conversation title that exceeds the reasonable length limit for filenames"
        self.mock_model.generate_content.return_value = mock_response
        
        messages = [
            Message(sender="Alice", timestamp="10:56:59 PM", content="Hello"),
            Message(sender="Bob", timestamp="10:57:05 PM", content="Hi")
        ]
        date = datetime(2025, 8, 4)
        
        filename = self.generator.generate_filename(messages, date)
        
        # Title should be truncated to 50 characters
        self.assertLessEqual(len(filename.split(' [')[0].split(' ', 1)[1]), 50)


if __name__ == '__main__':
    unittest.main()