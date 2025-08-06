import unittest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.main import process_file, _generate_standardized_filename
from src.tag_evaluator import TagEvaluator
from src.aim_parser import AIMParser


class TestIntegrationTagging(unittest.TestCase):
    
    def setUp(self):
        # Mock the API key environment variable
        self.api_key_patcher = patch.dict(os.environ, {'GEMINI_API_KEY': 'fake-api-key'})
        self.api_key_patcher.start()
        
        # Mock the Gemini API
        self.genai_patcher = patch('src.tag_evaluator.genai')
        self.mock_genai = self.genai_patcher.start()
        
        # Mock the filename generator genai as well
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
    
    def test_process_file_with_custom_tags(self):
        """Test processing file with custom tags"""
        # Create sample AIM conversation HTML
        sample_html = '''
        <B><FONT COLOR="#0000ff">Alice<!-- (10:56:59 PM)--></B></FONT>: <FONT>Can you help me with my math homework?</FONT><BR>
        <B><FONT COLOR="#ff0000">Bob<!-- (10:57:05 PM)--></B></FONT>: <FONT>Sure! What's the problem?</FONT><BR>
        <B><FONT COLOR="#0000ff">Alice<!-- (10:57:30 PM)--></B></FONT>: <FONT>I'm stuck on quadratic equations</FONT><BR>
        <B><FONT COLOR="#ff0000">Bob<!-- (10:58:00 PM)--></B></FONT>: <FONT>Let me help you understand the formula</FONT><BR>
        '''
        
        # Create temporary input file with a meaningful name for date extraction
        temp_dir = Path(tempfile.mkdtemp())
        input_path = temp_dir / "2025-08-04_conversation.htm"
        with open(input_path, 'w', encoding='utf-8') as f:
            f.write(sample_html)
        
        # Create temporary output file
        output_file = tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False)
        output_path = Path(output_file.name)
        output_file.close()
        
        try:
            # Test processing with custom tags
            custom_tags = ["homework-help", "math"]
            description = "Alice asks Bob for help with her math homework, specifically quadratic equations."
            
            process_file(input_path, output_path, description, custom_tags)
            
            # Read the output file
            with open(output_path, 'r', encoding='utf-8') as f:
                result = f.read()
            
            # Should contain description in frontmatter
            self.assertIn("description: Alice asks Bob for help with her math homework", result)
            
            # Should contain all tags including the default aim tag
            self.assertIn("- aim", result)
            self.assertIn("- homework-help", result) 
            self.assertIn("- math", result)
            
            # Should contain the conversation content
            self.assertIn("**Alice** (10:56:59 PM):", result)
            self.assertIn("Can you help me with my math homework?", result)
            self.assertIn("**Bob** (10:57:05 PM):", result)
            self.assertIn("Sure! What's the problem?", result)
        
        finally:
            input_path.unlink()
            temp_dir.rmdir()
            output_path.unlink()
    
    def test_process_file_without_custom_tags(self):
        """Test processing file without custom tags (default behavior)"""
        # Create sample AIM conversation HTML
        sample_html = '''
        <B><FONT COLOR="#0000ff">Alice<!-- (10:56:59 PM)--></B></FONT>: <FONT>Hey there!</FONT><BR>
        <B><FONT COLOR="#ff0000">Bob<!-- (10:57:05 PM)--></B></FONT>: <FONT>Hi Alice!</FONT><BR>
        '''
        
        # Create temporary input file with a meaningful name for date extraction
        temp_dir = Path(tempfile.mkdtemp())
        input_path = temp_dir / "2025-08-05_conversation.htm"
        with open(input_path, 'w', encoding='utf-8') as f:
            f.write(sample_html)
        
        # Create temporary output file
        output_file = tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False)
        output_path = Path(output_file.name)
        output_file.close()
        
        try:
            # Test processing without custom tags
            process_file(input_path, output_path)
            
            # Read the output file
            with open(output_path, 'r', encoding='utf-8') as f:
                result = f.read()
            
            # Should contain only the default aim tag
            self.assertIn("- aim", result)
            
            # Should not contain custom tags
            tag_section_start = result.find("tags:")
            tag_section_end = result.find("---", tag_section_start + 1)
            tags_section = result[tag_section_start:tag_section_end]
            
            # Count the number of tag lines (should be just "- aim")
            tag_lines = [line.strip() for line in tags_section.split('\n') if line.strip().startswith('-')]
            self.assertEqual(len(tag_lines), 1)
            self.assertEqual(tag_lines[0], "- aim")
        
        finally:
            input_path.unlink()
            temp_dir.rmdir()
            output_path.unlink()
    
    def test_generate_standardized_filename_with_tag_evaluator(self):
        """Test standardized filename generation with tag evaluation"""
        # Create sample AIM conversation HTML with sports content
        sample_html = '''
        <B><FONT COLOR="#0000ff">Alice<!-- (10:56:59 PM)--></B></FONT>: <FONT>Did you watch the basketball game last night?</FONT><BR>
        <B><FONT COLOR="#ff0000">Bob<!-- (10:57:05 PM)--></B></FONT>: <FONT>Yes! What a great game!</FONT><BR>
        <B><FONT COLOR="#0000ff">Alice<!-- (10:57:30 PM)--></B></FONT>: <FONT>The final quarter was amazing</FONT><BR>
        '''
        
        # Create tag configuration
        config_yaml = '''
tags:
  - name: sports
    description: This conversation contains a discussion of sports (e.g. baseball, basketball, football, etc.)
  - name: entertainment
    description: General entertainment discussions
'''
        
        # Create temporary files
        with tempfile.NamedTemporaryFile(mode='w', suffix='.htm', delete=False) as input_file:
            input_file.write(sample_html)
            input_path = Path(input_file.name)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as config_file:
            config_file.write(config_yaml)
            config_path = Path(config_file.name)
        
        try:
            # Create tag evaluator
            tag_evaluator = TagEvaluator(config_path)
            
            # Mock responses for filename generation and tag evaluation
            mock_responses = [
                MagicMock(text="Basketball game discussion"),  # For title generation
                MagicMock(text="Alice and Bob discuss last night's basketball game and share their excitement about the final quarter."),  # For description generation
                MagicMock(text="sports")  # For tag evaluation
            ]
            self.mock_model.generate_content.side_effect = mock_responses
            
            # Test filename generation with tag evaluator
            output_path, description, custom_tags = _generate_standardized_filename(input_path, tag_evaluator)
            
            # Should return expected values
            self.assertIn("Basketball game discussion", str(output_path))
            self.assertIn("Alice and Bob discuss", description)
            self.assertEqual(custom_tags, ["sports"])
            
        finally:
            input_path.unlink()
            config_path.unlink()
    
    def test_generate_standardized_filename_without_tag_evaluator(self):
        """Test standardized filename generation without tag evaluation"""
        # Create sample AIM conversation HTML
        sample_html = '''
        <B><FONT COLOR="#0000ff">Alice<!-- (10:56:59 PM)--></B></FONT>: <FONT>Hello there!</FONT><BR>
        <B><FONT COLOR="#ff0000">Bob<!-- (10:57:05 PM)--></B></FONT>: <FONT>Hi Alice!</FONT><BR>
        '''
        
        # Create temporary input file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.htm', delete=False) as input_file:
            input_file.write(sample_html)
            input_path = Path(input_file.name)
        
        try:
            # Mock responses for filename generation
            mock_responses = [
                MagicMock(text="Friendly greeting conversation"),  # For title generation
                MagicMock(text="Alice and Bob exchange friendly greetings.")  # For description generation
            ]
            self.mock_model.generate_content.side_effect = mock_responses
            
            # Test filename generation without tag evaluator
            output_path, description, custom_tags = _generate_standardized_filename(input_path)
            
            # Should return expected values
            self.assertIn("Friendly greeting conversation", str(output_path))
            self.assertIn("Alice and Bob exchange", description)
            self.assertEqual(custom_tags, [])  # No custom tags
            
        finally:
            input_path.unlink()
    
    def test_end_to_end_workflow_with_tag_config(self):
        """Test complete end-to-end workflow with tag configuration"""
        # Create sample AIM conversation HTML with multiple topics
        sample_html = '''
        <B><FONT COLOR="#0000ff">Alice<!-- (10:56:59 PM)--></B></FONT>: <FONT>Can you help me with my chemistry homework?</FONT><BR>
        <B><FONT COLOR="#ff0000">Bob<!-- (10:57:05 PM)--></B></FONT>: <FONT>Sure! What topic are you working on?</FONT><BR>
        <B><FONT COLOR="#0000ff">Alice<!-- (10:58:00 PM)--></B></FONT>: <FONT>Organic chemistry reactions</FONT><BR>
        <B><FONT COLOR="#ff0000">Bob<!-- (10:59:00 PM)--></B></FONT>: <FONT>Got it. Let me explain the mechanism.</FONT><BR>
        <B><FONT COLOR="#0000ff">Alice<!-- (11:05:00 PM)--></B></FONT>: <FONT>Thanks! By the way, are you going to the football game tomorrow?</FONT><BR>
        <B><FONT COLOR="#ff0000">Bob<!-- (11:05:30 PM)--></B></FONT>: <FONT>Definitely! It should be a great game.</FONT><BR>
        '''
        
        # Create tag configuration that matches the issue example
        config_yaml = '''
tags:
  - name: homework-help
    description: >
      This conversation contains a discussion of homework where one of the participants is assisting the other
      in completing an assignment.
  - name: sports
    description: >
      This conversation contains a discussion of sports (e.g. baseball, basketball, football, etc.) whether
      professional or otherwise.
'''
        
        # Create temporary files with meaningful names
        temp_dir = Path(tempfile.mkdtemp())
        input_path = temp_dir / "2025-08-05_homework_and_sports.htm"
        with open(input_path, 'w', encoding='utf-8') as f:
            f.write(sample_html)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as config_file:
            config_file.write(config_yaml)
            config_path = Path(config_file.name)
        
        try:
            # Create tag evaluator
            tag_evaluator = TagEvaluator(config_path)
            
            # Mock responses for filename generation and tag evaluation
            mock_responses = [
                MagicMock(text="Chemistry homework and football plans"),  # For title generation
                MagicMock(text="In this chat, Alice helps Bob work through some chemistry homework and then the two discuss the upcoming homecoming football game."),  # For description generation (matching issue example)
                MagicMock(text="homework-help\nsports")  # For tag evaluation (both tags match)
            ]
            self.mock_model.generate_content.side_effect = mock_responses
            
            # Generate filename and tags
            output_path, description, custom_tags = _generate_standardized_filename(input_path, tag_evaluator)
            
            # Create temporary output file
            output_file = tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False)
            final_output_path = Path(output_file.name)
            output_file.close()
            
            # Process the file with the generated tags
            process_file(input_path, final_output_path, description, custom_tags)
            
            # Read the final result
            with open(final_output_path, 'r', encoding='utf-8') as f:
                result = f.read()
            
            # Verify the result matches the issue example format
            self.assertIn("description: In this chat, Alice helps Bob work through some chemistry homework", result)
            
            # Should contain all expected tags
            self.assertIn("- aim", result)
            self.assertIn("- homework-help", result)
            self.assertIn("- sports", result)
            
            # Should contain conversation content
            self.assertIn("chemistry homework", result)
            self.assertIn("football game", result)
            
            final_output_path.unlink()
            
        finally:
            input_path.unlink()
            temp_dir.rmdir()
            config_path.unlink()


    def test_default_config_file_loading(self):
        """Test that config.yaml is automatically loaded from current directory"""
        # Create sample conversation and config
        sample_html = '''
        <B><FONT COLOR="#0000ff">Alice<!-- (10:56:59 PM)--></B></FONT>: <FONT>Let's play some video games!</FONT><BR>
        <B><FONT COLOR="#ff0000">Bob<!-- (10:57:05 PM)--></B></FONT>: <FONT>Great idea! What game?</FONT><BR>
        '''
        
        config_yaml = '''
tags:
  - name: gaming
    description: This conversation contains discussions about video games
'''
        
        # Create temporary files
        temp_dir = Path(tempfile.mkdtemp())
        input_path = temp_dir / "2025-08-05_gaming.htm"
        config_path = temp_dir / "config.yaml"
        
        with open(input_path, 'w', encoding='utf-8') as f:
            f.write(sample_html)
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(config_yaml)
        
        # Change to temp directory so config.yaml is found
        original_cwd = Path.cwd()
        try:
            os.chdir(temp_dir)
            
            # Create tag evaluator with automatic config detection
            tag_evaluator = TagEvaluator()
            
            # Mock response for tag evaluation
            mock_response = MagicMock()
            mock_response.text = "gaming"
            self.mock_model.generate_content.return_value = mock_response
            
            # Parse messages and evaluate tags
            parser = AIMParser()
            with open(input_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            messages = parser.parse(html_content)
            
            # Should find and load the config automatically
            custom_tags = tag_evaluator.evaluate_tags(messages)
            self.assertEqual(custom_tags, ["gaming"])
            
        finally:
            os.chdir(original_cwd)
            input_path.unlink()
            config_path.unlink()
            temp_dir.rmdir()


if __name__ == '__main__':
    unittest.main()