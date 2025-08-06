import unittest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.tag_evaluator import TagEvaluator, ParticipantConfig
from src.main import _generate_standardized_filename, process_file
from src.aim_parser import AIMParser
from src.filename_generator import FilenameGenerator


class TestParticipantSystem(unittest.TestCase):
    
    def setUp(self):
        # Mock the API key environment variable
        self.api_key_patcher = patch.dict(os.environ, {'GEMINI_API_KEY': 'fake-api-key'})
        self.api_key_patcher.start()
        
        # Mock the Gemini API for TagEvaluator
        self.genai_patcher = patch('src.tag_evaluator.genai')
        self.mock_genai = self.genai_patcher.start()
        
        # Mock the Gemini API for FilenameGenerator
        self.genai_patcher_fg = patch('src.filename_generator.genai')
        self.mock_genai_fg = self.genai_patcher_fg.start()
        
        # Mock the model and response
        self.mock_model = MagicMock()
        self.mock_genai.GenerativeModel.return_value = self.mock_model
        self.mock_genai_fg.GenerativeModel.return_value = self.mock_model
    
    def tearDown(self):
        self.api_key_patcher.stop()
        self.genai_patcher.stop()
        self.genai_patcher_fg.stop()
    
    def test_participant_config_creation(self):
        """Test creating ParticipantConfig objects"""
        config = ParticipantConfig("Bob", "bob123", "[[Bob Smith]]")
        self.assertEqual(config.name, "Bob")
        self.assertEqual(config.aim, "bob123")
        self.assertEqual(config.md, "[[Bob Smith]]")
    
    def test_load_participant_configuration_from_yaml(self):
        """Test loading participant configuration from YAML file"""
        config_yaml = '''
tags:
  - name: homework-help
    description: This conversation contains homework discussion

participants:
  - name: Bob
    aim: bob123
    md: "[[Bob Smith]]"
  - name: Alice
    aim: alice456
    md: "[[Alice Sanders]]"
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as config_file:
            config_file.write(config_yaml)
            config_path = Path(config_file.name)
        
        try:
            evaluator = TagEvaluator(config_path)
            
            # Should have loaded participant configurations
            self.assertEqual(len(evaluator.participant_configs), 2)
            
            # Check first participant
            bob_config = evaluator.participant_configs[0]
            self.assertEqual(bob_config.name, "Bob")
            self.assertEqual(bob_config.aim, "bob123")
            self.assertEqual(bob_config.md, "[[Bob Smith]]")
            
            # Check second participant
            alice_config = evaluator.participant_configs[1]
            self.assertEqual(alice_config.name, "Alice")
            self.assertEqual(alice_config.aim, "alice456")
            self.assertEqual(alice_config.md, "[[Alice Sanders]]")
            
        finally:
            config_path.unlink()
    
    def test_load_configuration_with_missing_participant_fields(self):
        """Test loading configuration with invalid participant entries"""
        config_yaml = '''
participants:
  - name: Bob
    aim: bob123
    md: "[[Bob Smith]]"
  - name: Alice
    # Missing aim field
    md: "[[Alice Sanders]]"
  - aim: charlie789
    # Missing name field
    md: "[[Charlie Brown]]"
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as config_file:
            config_file.write(config_yaml)
            config_path = Path(config_file.name)
        
        try:
            evaluator = TagEvaluator(config_path)
            
            # Should only load the valid participant config
            self.assertEqual(len(evaluator.participant_configs), 1)
            self.assertEqual(evaluator.participant_configs[0].name, "Bob")
            
        finally:
            config_path.unlink()
    
    def test_map_participants_with_config(self):
        """Test mapping AIM handles to markdown links with configuration"""
        config_yaml = '''
participants:
  - name: Bob
    aim: bob123
    md: "[[Bob Smith]]"
  - name: Alice
    aim: alice456
    md: "[[Alice Sanders]]"
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as config_file:
            config_file.write(config_yaml)
            config_path = Path(config_file.name)
        
        try:
            evaluator = TagEvaluator(config_path)
            
            # Test mapping participants
            aim_handles = ["bob123", "alice456", "unknown_user"]
            mapped_participants = evaluator.map_participants(aim_handles)
            
            self.assertEqual(len(mapped_participants), 3)
            self.assertEqual(mapped_participants[0], "[[Bob Smith]]")
            self.assertEqual(mapped_participants[1], "[[Alice Sanders]]")
            self.assertEqual(mapped_participants[2], "unknown_user")  # Falls back to AIM handle
            
        finally:
            config_path.unlink()
    
    def test_map_participants_without_config(self):
        """Test mapping participants without configuration (fallback behavior)"""
        evaluator = TagEvaluator()  # No config file
        
        aim_handles = ["bob123", "alice456"]
        mapped_participants = evaluator.map_participants(aim_handles)
        
        # Should fall back to AIM handles
        self.assertEqual(mapped_participants, ["bob123", "alice456"])
    
    def test_get_human_readable_names_with_config(self):
        """Test getting human-readable names with configuration"""
        config_yaml = '''
participants:
  - name: Bob
    aim: bob123
    md: "[[Bob Smith]]"
  - name: Alice
    aim: alice456
    md: "[[Alice Sanders]]"
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as config_file:
            config_file.write(config_yaml)
            config_path = Path(config_file.name)
        
        try:
            evaluator = TagEvaluator(config_path)
            
            # Test getting human-readable names
            aim_handles = ["bob123", "alice456", "unknown_user"]
            name_mapping = evaluator.get_human_readable_names(aim_handles)
            
            self.assertEqual(len(name_mapping), 3)
            self.assertEqual(name_mapping["bob123"], "Bob")
            self.assertEqual(name_mapping["alice456"], "Alice")
            self.assertEqual(name_mapping["unknown_user"], "unknown_user")  # Falls back to handle
            
        finally:
            config_path.unlink()
    
    def test_get_human_readable_names_without_config(self):
        """Test getting human-readable names without configuration (fallback behavior)"""
        evaluator = TagEvaluator()  # No config file
        
        aim_handles = ["bob123", "alice456"]
        name_mapping = evaluator.get_human_readable_names(aim_handles)
        
        # Should fall back to AIM handles
        expected_mapping = {"bob123": "bob123", "alice456": "alice456"}
        self.assertEqual(name_mapping, expected_mapping)
    
    def test_filename_generation_with_human_readable_names(self):
        """Test that filename generation uses human-readable names when available"""
        config_yaml = '''
participants:
  - name: Bob
    aim: bob123
    md: "[[Bob Smith]]"
  - name: Alice
    aim: alice456
    md: "[[Alice Sanders]]"
'''
        
        sample_html = '''
        <B><FONT COLOR="#0000ff">bob123<!-- (10:56:59 PM)--></B></FONT>: <FONT>Can you help me with homework?</FONT><BR>
        <B><FONT COLOR="#ff0000">alice456<!-- (10:57:05 PM)--></B></FONT>: <FONT>Sure! What subject?</FONT><BR>
        '''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as config_file:
            config_file.write(config_yaml)
            config_path = Path(config_file.name)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.htm', delete=False) as input_file:
            input_file.write(sample_html)
            input_path = Path(input_file.name)
        
        try:
            evaluator = TagEvaluator(config_path)
            
            # Mock responses for filename and description generation
            mock_responses = [
                MagicMock(text="Homework help discussion"),  # For title generation
                MagicMock(text="In this conversation, Bob asks Alice for help with homework.")  # For description generation
            ]
            self.mock_model.generate_content.side_effect = mock_responses
            
            # Generate filename with participant mapping
            output_path, description, custom_tags, participants = _generate_standardized_filename(input_path, evaluator)
            
            # Should contain human-readable names in description
            self.assertIn("Bob asks Alice", description)
            
            # Should contain mapped participants
            self.assertIn("[[Bob Smith]]", participants)
            self.assertIn("[[Alice Sanders]]", participants)
            
        finally:
            config_path.unlink()
            input_path.unlink()
    
    def test_markdown_output_with_participants_frontmatter(self):
        """Test that markdown output includes participants in frontmatter"""
        config_yaml = '''
participants:
  - name: Bob
    aim: bob123
    md: "[[Bob Smith]]"
  - name: Alice  
    aim: alice456
    md: "[[Alice Sanders]]"
'''
        
        sample_html = '''
        <B><FONT COLOR="#0000ff">bob123<!-- (10:56:59 PM)--></B></FONT>: <FONT>Hello there!</FONT><BR>
        <B><FONT COLOR="#ff0000">alice456<!-- (10:57:05 PM)--></B></FONT>: <FONT>Hi Bob!</FONT><BR>
        '''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as config_file:
            config_file.write(config_yaml)
            config_path = Path(config_file.name)
        
        # Create input file with meaningful name for date extraction
        temp_dir = Path(tempfile.mkdtemp())
        input_path = temp_dir / "2025-08-06_conversation.htm"
        with open(input_path, 'w', encoding='utf-8') as f:
            f.write(sample_html)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as output_file:
            output_path = Path(output_file.name)
        
        try:
            evaluator = TagEvaluator(config_path)
            
            # Mock responses
            mock_responses = [
                MagicMock(text="Friendly greeting"),  # Title
                MagicMock(text="Bob and Alice exchange friendly greetings.")  # Description
            ]
            self.mock_model.generate_content.side_effect = mock_responses
            
            # Generate filename and process
            _, description, custom_tags, participants = _generate_standardized_filename(input_path, evaluator)
            process_file(input_path, output_path, description, custom_tags, participants)
            
            # Read the output
            with open(output_path, 'r', encoding='utf-8') as f:
                result = f.read()
            
            # Should contain participants in frontmatter
            self.assertIn("participants:", result)
            self.assertIn("- [[Bob Smith]]", result)
            self.assertIn("- [[Alice Sanders]]", result)
            
            # Should contain human-readable names in description
            self.assertIn("Bob and Alice exchange", result)
            
        finally:
            config_path.unlink()
            input_path.unlink()
            temp_dir.rmdir()
            output_path.unlink()
    
    def test_empty_participants_list(self):
        """Test behavior with empty participants list"""
        evaluator = TagEvaluator()
        
        # Empty list should return empty list
        mapped_participants = evaluator.map_participants([])
        self.assertEqual(mapped_participants, [])
        
        name_mapping = evaluator.get_human_readable_names([])
        self.assertEqual(name_mapping, {})
    
    def test_configuration_with_only_tags_no_participants(self):
        """Test configuration file with only tags, no participants section"""
        config_yaml = '''
tags:
  - name: homework-help
    description: This conversation contains homework discussion
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as config_file:
            config_file.write(config_yaml)
            config_path = Path(config_file.name)
        
        try:
            evaluator = TagEvaluator(config_path)
            
            # Should have loaded tags but no participants
            self.assertEqual(len(evaluator.tag_configs), 1)
            self.assertEqual(len(evaluator.participant_configs), 0)
            
            # Participant mapping should fall back to handles
            aim_handles = ["bob123", "alice456"]
            mapped_participants = evaluator.map_participants(aim_handles)
            self.assertEqual(mapped_participants, ["bob123", "alice456"])
            
        finally:
            config_path.unlink()


if __name__ == '__main__':
    unittest.main()