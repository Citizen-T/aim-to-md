import unittest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.tag_evaluator import TagEvaluator, TagConfig
from src.aim_parser import Message


class TestTagConfig(unittest.TestCase):
    def test_init(self):
        """Test TagConfig initialization"""
        config = TagConfig("homework-help", "Conversations about homework assistance")
        self.assertEqual(config.name, "homework-help")
        self.assertEqual(config.description, "Conversations about homework assistance")
    
    def test_repr(self):
        """Test TagConfig string representation"""
        config = TagConfig("sports", "Sports discussions")
        expected = "TagConfig(name='sports', description='Sports discussions')"
        self.assertEqual(repr(config), expected)


class TestTagEvaluator(unittest.TestCase):
    def setUp(self):
        # Mock the API key environment variable
        self.api_key_patcher = patch.dict(os.environ, {'GEMINI_API_KEY': 'fake-api-key'})
        self.api_key_patcher.start()
        
        # Mock the Gemini API
        self.genai_patcher = patch('src.tag_evaluator.genai')
        self.mock_genai = self.genai_patcher.start()
        
        # Mock the model and response
        self.mock_model = MagicMock()
        self.mock_genai.GenerativeModel.return_value = self.mock_model
    
    def tearDown(self):
        self.api_key_patcher.stop()
        self.genai_patcher.stop()
    
    def test_init_without_config_file(self):
        """Test TagEvaluator initialization without config file"""
        evaluator = TagEvaluator()
        self.assertEqual(evaluator.tag_configs, [])
    
    def test_init_with_nonexistent_config_file(self):
        """Test TagEvaluator initialization with non-existent config file"""
        nonexistent_path = Path("/nonexistent/path/config.yaml")
        evaluator = TagEvaluator(nonexistent_path)
        self.assertEqual(evaluator.tag_configs, [])
    
    def test_init_without_api_key(self):
        """Test that TagEvaluator raises error when API key is missing"""
        with patch.dict(os.environ, {}, clear=True), \
             patch('src.tag_evaluator.load_dotenv'):
            with self.assertRaises(ValueError) as cm:
                TagEvaluator()
            self.assertIn("Please set it in your .env file or environment variables", str(cm.exception))
    
    def test_load_valid_config(self):
        """Test loading valid YAML configuration"""
        config_yaml = """
tags:
  - name: homework-help
    description: >
      This conversation contains a discussion of homework where one of the participants is assisting the other
      in completing an assignment.
  - name: sports
    description: >
      This conversation contains a discussion of sports (e.g. baseball, basketball, football, etc.) whether
      professional or otherwise.
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_yaml)
            config_path = Path(f.name)
        
        try:
            evaluator = TagEvaluator(config_path)
            self.assertEqual(len(evaluator.tag_configs), 2)
            
            # Check first tag
            self.assertEqual(evaluator.tag_configs[0].name, "homework-help")
            self.assertIn("homework", evaluator.tag_configs[0].description)
            
            # Check second tag
            self.assertEqual(evaluator.tag_configs[1].name, "sports")
            self.assertIn("sports", evaluator.tag_configs[1].description)
        finally:
            config_path.unlink()
    
    def test_load_config_missing_tags_section(self):
        """Test loading config without tags section"""
        config_yaml = """
other_config:
  - name: something
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_yaml)
            config_path = Path(f.name)
        
        try:
            evaluator = TagEvaluator(config_path)
            self.assertEqual(len(evaluator.tag_configs), 0)
        finally:
            config_path.unlink()
    
    def test_load_config_invalid_tag_entry(self):
        """Test loading config with invalid tag entry"""
        config_yaml = """
tags:
  - name: homework-help
    description: Valid tag description
  - name_missing: sports
    description: Missing name field
  - name: incomplete
    # Missing description field
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_yaml)
            config_path = Path(f.name)
        
        try:
            with patch('builtins.print') as mock_print:
                evaluator = TagEvaluator(config_path)
                # Should only load the valid tag
                self.assertEqual(len(evaluator.tag_configs), 1)
                self.assertEqual(evaluator.tag_configs[0].name, "homework-help")
                # Should print warnings for invalid entries
                self.assertTrue(mock_print.called)
        finally:
            config_path.unlink()
    
    def test_evaluate_tags_empty_messages(self):
        """Test tag evaluation with empty message list"""
        evaluator = TagEvaluator()
        result = evaluator.evaluate_tags([])
        self.assertEqual(result, [])
    
    def test_evaluate_tags_no_configs(self):
        """Test tag evaluation with no tag configurations"""
        messages = [
            Message(sender="Alice", timestamp="10:56:59 PM", content="Hello"),
            Message(sender="Bob", timestamp="10:57:05 PM", content="Hi")
        ]
        
        evaluator = TagEvaluator()
        result = evaluator.evaluate_tags(messages)
        self.assertEqual(result, [])
    
    def test_evaluate_tags_only_system_messages(self):
        """Test tag evaluation with only system messages"""
        config_yaml = """
tags:
  - name: test-tag
    description: Any conversation
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_yaml)
            config_path = Path(f.name)
        
        try:
            evaluator = TagEvaluator(config_path)
            
            messages = [
                Message(sender="System", timestamp="", content="Alice signed on", is_system_message=True),
                Message(sender="System", timestamp="", content="Bob signed off", is_system_message=True)
            ]
            
            result = evaluator.evaluate_tags(messages)
            self.assertEqual(result, [])
        finally:
            config_path.unlink()
    
    def test_evaluate_tags_success(self):
        """Test successful tag evaluation"""
        config_yaml = """
tags:
  - name: homework-help
    description: Conversations about homework assistance
  - name: sports
    description: Sports discussions
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_yaml)
            config_path = Path(f.name)
        
        try:
            evaluator = TagEvaluator(config_path)
            
            # Setup mock response
            mock_response = MagicMock()
            mock_response.text = "homework-help\nsports"
            self.mock_model.generate_content.return_value = mock_response
            
            messages = [
                Message(sender="Alice", timestamp="10:56:59 PM", content="Can you help me with my math homework?"),
                Message(sender="Bob", timestamp="10:57:05 PM", content="Sure! What's the problem?"),
                Message(sender="Alice", timestamp="10:58:00 PM", content="Did you see the football game yesterday?")
            ]
            
            result = evaluator.evaluate_tags(messages)
            
            # Should return both matching tags
            self.assertCountEqual(result, ["homework-help", "sports"])
            
            # Verify API was called
            self.mock_model.generate_content.assert_called_once()
            
            # Check that the prompt includes the conversation and tag descriptions
            call_args = self.mock_model.generate_content.call_args[0][0]
            self.assertIn("homework-help: Conversations about homework assistance", call_args)
            self.assertIn("sports: Sports discussions", call_args)
            self.assertIn("Alice: Can you help me with my math homework?", call_args)
            self.assertIn("Bob: Sure! What's the problem?", call_args)
        finally:
            config_path.unlink()
    
    def test_evaluate_tags_partial_match(self):
        """Test tag evaluation with partial matches"""
        config_yaml = """
tags:
  - name: homework-help
    description: Conversations about homework assistance
  - name: sports
    description: Sports discussions
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_yaml)
            config_path = Path(f.name)
        
        try:
            evaluator = TagEvaluator(config_path)
            
            # Setup mock response - only one tag matches
            mock_response = MagicMock()
            mock_response.text = "homework-help"
            self.mock_model.generate_content.return_value = mock_response
            
            messages = [
                Message(sender="Alice", timestamp="10:56:59 PM", content="Can you help me with my math homework?"),
                Message(sender="Bob", timestamp="10:57:05 PM", content="Sure! What's the problem?")
            ]
            
            result = evaluator.evaluate_tags(messages)
            
            # Should return only the matching tag
            self.assertEqual(result, ["homework-help"])
        finally:
            config_path.unlink()
    
    def test_evaluate_tags_no_match(self):
        """Test tag evaluation with no matches"""
        config_yaml = """
tags:
  - name: homework-help
    description: Conversations about homework assistance
  - name: sports
    description: Sports discussions
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_yaml)
            config_path = Path(f.name)
        
        try:
            evaluator = TagEvaluator(config_path)
            
            # Setup mock response - no matches
            mock_response = MagicMock()
            mock_response.text = ""
            self.mock_model.generate_content.return_value = mock_response
            
            messages = [
                Message(sender="Alice", timestamp="10:56:59 PM", content="How was your day?"),
                Message(sender="Bob", timestamp="10:57:05 PM", content="Pretty good, thanks!")
            ]
            
            result = evaluator.evaluate_tags(messages)
            
            # Should return empty list
            self.assertEqual(result, [])
        finally:
            config_path.unlink()
    
    def test_evaluate_tags_invalid_response(self):
        """Test tag evaluation with invalid LLM response"""
        config_yaml = """
tags:
  - name: homework-help
    description: Conversations about homework assistance
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_yaml)
            config_path = Path(f.name)
        
        try:
            evaluator = TagEvaluator(config_path)
            
            # Setup mock response with invalid tag names
            mock_response = MagicMock()
            mock_response.text = "invalid-tag\nnonexistent-tag\nhomework-help"
            self.mock_model.generate_content.return_value = mock_response
            
            messages = [
                Message(sender="Alice", timestamp="10:56:59 PM", content="Can you help me with homework?")
            ]
            
            result = evaluator.evaluate_tags(messages)
            
            # Should only return the valid tag
            self.assertEqual(result, ["homework-help"])
        finally:
            config_path.unlink()
    
    def test_evaluate_tags_api_error(self):
        """Test handling of LLM API errors"""
        config_yaml = """
tags:
  - name: homework-help
    description: Conversations about homework assistance
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_yaml)
            config_path = Path(f.name)
        
        try:
            evaluator = TagEvaluator(config_path)
            
            # Setup mock to raise an exception
            self.mock_model.generate_content.side_effect = Exception("API Error")
            
            messages = [
                Message(sender="Alice", timestamp="10:56:59 PM", content="Hello")
            ]
            
            with patch('builtins.print') as mock_print:
                result = evaluator.evaluate_tags(messages)
                
                # Should return empty list and print warning
                self.assertEqual(result, [])
                mock_print.assert_called_with("Warning: Failed to evaluate tags using Gemini API: API Error")
        finally:
            config_path.unlink()
    
    def test_sample_conversation_content_small_conversation(self):
        """Test conversation sampling with small conversations"""
        evaluator = TagEvaluator()
        
        # Small conversation should not be sampled
        content = [f"Message {i}" for i in range(1, 21)]  # 20 messages
        result = evaluator._sample_conversation_content(content, max_messages=50)
        
        # Should contain all messages
        for i in range(1, 21):
            self.assertIn(f"Message {i}", result)
        
        # Should not contain sampling markers
        self.assertNotIn("... [conversation continues] ...", result)
        self.assertNotIn("... [end of conversation] ...", result)
    
    def test_sample_conversation_content_large_conversation(self):
        """Test conversation sampling with large conversations"""
        evaluator = TagEvaluator()
        
        # Large conversation that should be sampled
        content = [f"Message {i}" for i in range(1, 201)]  # 200 messages
        result = evaluator._sample_conversation_content(content, max_messages=50)
        
        # Should contain early messages
        self.assertIn("Message 1", result)
        self.assertIn("Message 10", result)
        
        # Should contain late messages
        self.assertIn("Message 200", result)
        self.assertIn("Message 191", result)
        
        # Should contain sampling markers
        self.assertIn("... [conversation continues] ...", result)
        self.assertIn("... [end of conversation] ...", result)


if __name__ == '__main__':
    unittest.main()