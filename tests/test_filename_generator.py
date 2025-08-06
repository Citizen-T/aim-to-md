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
        with patch.dict(os.environ, {}, clear=True), \
             patch('src.filename_generator.load_dotenv'):
            with self.assertRaises(ValueError) as cm:
                FilenameGenerator()
            self.assertIn("Please set it in your .env file or environment variables", str(cm.exception))
    
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
    
    def test_generate_description_success(self):
        """Test successful description generation with LLM"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.text = "In this conversation Alice and Bob discuss their weekend plans and decide to go hiking together."
        self.mock_model.generate_content.return_value = mock_response
        
        messages = [
            Message(sender="Alice", timestamp="10:56:59 PM", content="What are you doing this weekend?"),
            Message(sender="Bob", timestamp="10:57:05 PM", content="I was thinking of going hiking"),
            Message(sender="Alice", timestamp="10:57:10 PM", content="That sounds great! Can I join you?"),
            Message(sender="Bob", timestamp="10:57:15 PM", content="Of course!")
        ]
        
        description = self.generator.generate_description(messages)
        
        expected = "In this conversation Alice and Bob discuss their weekend plans and decide to go hiking together."
        self.assertEqual(description, expected)
        self.mock_model.generate_content.assert_called_once()
    
    def test_generate_description_empty_messages(self):
        """Test description generation with empty message list"""
        description = self.generator.generate_description([])
        self.assertEqual(description, "Empty conversation")
    
    def test_generate_description_only_system_messages(self):
        """Test description generation with only system messages"""
        messages = [
            Message(sender="System", timestamp="", content="Alice signed on", is_system_message=True),
            Message(sender="System", timestamp="", content="Bob signed off", is_system_message=True)
        ]
        
        description = self.generator.generate_description(messages)
        self.assertEqual(description, "Conversation with only system messages")
    
    def test_generate_description_with_system_messages_mixed(self):
        """Test description generation filtering out system messages"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.text = "Alice greets Bob in a friendly conversation."
        self.mock_model.generate_content.return_value = mock_response
        
        messages = [
            Message(sender="System", timestamp="", content="Alice signed on", is_system_message=True),
            Message(sender="Alice", timestamp="10:56:59 PM", content="Hello Bob!"),
            Message(sender="Bob", timestamp="10:57:05 PM", content="Hi Alice!"),
            Message(sender="System", timestamp="", content="Bob signed off", is_system_message=True)
        ]
        
        description = self.generator.generate_description(messages)
        
        self.assertEqual(description, "Alice greets Bob in a friendly conversation.")
        # Verify the system messages were filtered out in the prompt
        call_args = self.mock_model.generate_content.call_args[0][0]
        self.assertNotIn("Alice signed on", call_args)
        self.assertNotIn("Bob signed off", call_args)
        self.assertIn("Alice: Hello Bob!", call_args)
        self.assertIn("Bob: Hi Alice!", call_args)
    
    def test_generate_description_api_error(self):
        """Test handling of LLM API errors in description generation"""
        # Setup mock to raise an exception
        self.mock_model.generate_content.side_effect = Exception("API Error")
        
        messages = [
            Message(sender="Alice", timestamp="10:56:59 PM", content="Hello"),
            Message(sender="Bob", timestamp="10:57:05 PM", content="Hi")
        ]
        
        with self.assertRaises(RuntimeError) as cm:
            self.generator.generate_description(messages)
        
        self.assertIn("Failed to generate description using Gemini API", str(cm.exception))
    
    def test_generate_description_with_quotes(self):
        """Test handling of LLM response with quotes in description"""
        # Setup mock response with quotes
        mock_response = MagicMock()
        mock_response.text = '"Alice and Bob catch up on recent events and make plans for the future."'
        self.mock_model.generate_content.return_value = mock_response
        
        messages = [
            Message(sender="Alice", timestamp="10:56:59 PM", content="How have you been?"),
            Message(sender="Bob", timestamp="10:57:05 PM", content="Pretty good, you?")
        ]
        
        description = self.generator.generate_description(messages)
        
        # Quotes should be removed
        expected = "Alice and Bob catch up on recent events and make plans for the future."
        self.assertEqual(description, expected)
    
    def test_generate_description_too_short(self):
        """Test handling of very short LLM responses"""
        # Setup mock response that's too short
        mock_response = MagicMock()
        mock_response.text = "Chat"
        self.mock_model.generate_content.return_value = mock_response
        
        messages = [
            Message(sender="Alice", timestamp="10:56:59 PM", content="Hi"),
            Message(sender="Bob", timestamp="10:57:05 PM", content="Hello")
        ]
        
        description = self.generator.generate_description(messages)
        
        # Should use fallback for short responses
        self.assertEqual(description, "Brief conversation between participants")
    
    def test_generate_description_long_response(self):
        """Test handling of long LLM responses without truncation"""
        # Setup mock response that's long
        long_text = "This is a very long description that demonstrates the AI's ability to generate comprehensive descriptions without artificial length limits. The conversation covers multiple topics including planning activities, discussing personal updates, and making future arrangements."
        mock_response = MagicMock()
        mock_response.text = long_text
        self.mock_model.generate_content.return_value = mock_response
        
        messages = [
            Message(sender="Alice", timestamp="10:56:59 PM", content="Hello"),
            Message(sender="Bob", timestamp="10:57:05 PM", content="Hi there")
        ]
        
        description = self.generator.generate_description(messages)
        
        # Should return the full description without truncation
        self.assertEqual(description, long_text)
        # Should be longer than the old 300 character limit
        self.assertGreater(len(description), 200)
    
    def test_generate_description_message_sampling(self):
        """Test that description generation uses smart sampling for long conversations"""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.text = "Long conversation between Alice and Bob covering many topics."
        self.mock_model.generate_content.return_value = mock_response
        
        # Create more than 100 messages to trigger sampling
        messages = []
        for i in range(120):
            messages.append(Message(sender="Alice" if i % 2 == 0 else "Bob", 
                                  timestamp="10:56:59 PM", 
                                  content=f"Message {i+1}"))
        
        description = self.generator.generate_description(messages)
        
        # Verify the prompt includes messages from different parts of conversation
        call_args = self.mock_model.generate_content.call_args[0][0]
        
        # Should include early messages
        self.assertIn("Message 1", call_args)
        
        # Should include late messages  
        self.assertIn("Message 120", call_args)
        
        # Should include conversation separator markers for sampled content
        self.assertIn("... [conversation continues] ...", call_args)
        self.assertIn("... [end of conversation] ...", call_args)
        
        self.assertEqual(description, "Long conversation between Alice and Bob covering many topics.")
    
    def test_sample_conversation_content_small_conversation(self):
        """Test that small conversations are not sampled"""
        generator = FilenameGenerator()
        
        # Small conversation should use all messages
        content = [f"Message {i}" for i in range(1, 21)]  # 20 messages
        result = generator._sample_conversation_content(content, max_messages=50)
        
        # Should contain all messages
        for i in range(1, 21):
            self.assertIn(f"Message {i}", result)
        
        # Should not contain sampling markers
        self.assertNotIn("... [conversation continues] ...", result)
        self.assertNotIn("... [end of conversation] ...", result)
    
    def test_sample_conversation_content_large_conversation(self):
        """Test that large conversations are intelligently sampled"""
        generator = FilenameGenerator()
        
        # Large conversation that should be sampled
        content = [f"Message {i}" for i in range(1, 201)]  # 200 messages
        result = generator._sample_conversation_content(content, max_messages=50)
        
        # Should contain early messages
        self.assertIn("Message 1", result)
        self.assertIn("Message 10", result)
        
        # Should contain late messages
        self.assertIn("Message 200", result)
        self.assertIn("Message 191", result)
        
        # Should contain sampling markers
        self.assertIn("... [conversation continues] ...", result)
        self.assertIn("... [end of conversation] ...", result)
        
        # Should not exceed max_messages (plus separators)
        lines = result.split('\n')
        non_separator_lines = [line for line in lines if not line.startswith('... [')]
        self.assertLessEqual(len(non_separator_lines), 50)


if __name__ == '__main__':
    unittest.main()