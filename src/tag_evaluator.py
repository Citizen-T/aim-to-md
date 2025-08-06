import os
import yaml
from typing import List, Dict, Any, Optional
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv
from src.aim_parser import Message


class TagConfig:
    """Represents a single tag configuration."""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    def __repr__(self):
        return f"TagConfig(name='{self.name}', description='{self.description}')"


class ParticipantConfig:
    """Represents a single participant configuration."""
    
    def __init__(self, name: str, aim: str, md: str):
        self.name = name
        self.aim = aim
        self.md = md
    
    def __repr__(self):
        return f"ParticipantConfig(name='{self.name}', aim='{self.aim}', md='{self.md}')"


class TagEvaluator:
    """Evaluates which custom tags should be applied to conversations using LLM."""
    
    def __init__(self, config_file_path: Optional[Path] = None):
        # Load environment variables
        load_dotenv()
        
        # Configure Gemini API
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is required. "
                "Please set it in your .env file or environment variables."
            )
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite')
        
        # Load tag configurations and participant configurations
        self.tag_configs = []
        self.participant_configs = []
        
        # Determine config file to use
        config_to_load = None
        if config_file_path and config_file_path.exists():
            config_to_load = config_file_path
        elif config_file_path is None:
            # Check for default config.yaml in current directory
            default_config = Path("config.yaml")
            if default_config.exists():
                config_to_load = default_config
        
        if config_to_load:
            self.tag_configs, self.participant_configs = self._load_config(config_to_load)
    
    def _load_config(self, config_file_path: Path) -> tuple[List[TagConfig], List[ParticipantConfig]]:
        """Load tag and participant configurations from YAML file."""
        try:
            with open(config_file_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            if not config_data:
                return [], []
            
            # Load tag configurations
            tag_configs = []
            if 'tags' in config_data:
                for tag_data in config_data['tags']:
                    if 'name' in tag_data and 'description' in tag_data:
                        tag_configs.append(TagConfig(
                            name=tag_data['name'],
                            description=tag_data['description'].strip()
                        ))
                    else:
                        print(f"Warning: Skipping invalid tag configuration: {tag_data}")
            
            # Load participant configurations
            participant_configs = []
            if 'participants' in config_data:
                for participant_data in config_data['participants']:
                    if 'name' in participant_data and 'aim' in participant_data and 'md' in participant_data:
                        participant_configs.append(ParticipantConfig(
                            name=participant_data['name'],
                            aim=participant_data['aim'],
                            md=participant_data['md']
                        ))
                    else:
                        print(f"Warning: Skipping invalid participant configuration: {participant_data}")
            
            return tag_configs, participant_configs
            
        except (yaml.YAMLError, IOError) as e:
            print(f"Warning: Could not load configuration from {config_file_path}: {e}")
            return [], []
    
    def evaluate_tags(self, messages: List[Message]) -> List[str]:
        """
        Evaluate which custom tags should be applied to the conversation.
        
        Returns:
            List of tag names that match the conversation content.
        """
        if not self.tag_configs or not messages:
            return []
        
        # Filter out system messages for tag evaluation
        regular_messages = [msg for msg in messages if not msg.is_system_message]
        if not regular_messages:
            return []
        
        # Prepare conversation content for the LLM
        conversation_content = []
        for message in regular_messages:
            conversation_content.append(f"{message.sender}: {message.content}")
        
        # Limit to reasonable number of messages (use sampling if needed)
        max_messages = 100
        if len(conversation_content) > max_messages:
            # Use similar sampling strategy as FilenameGenerator
            conversation_text = self._sample_conversation_content(conversation_content, max_messages)
        else:
            conversation_text = "\n".join(conversation_content)
        
        # Create tag evaluation prompt
        tag_descriptions = []
        for config in self.tag_configs:
            tag_descriptions.append(f"- {config.name}: {config.description}")
        
        prompt = f"""Based on this AIM conversation, determine which of the following custom tags apply to the conversation content. Only return the tag names that clearly match the conversation, one per line.

Available tags:
{chr(10).join(tag_descriptions)}

Conversation:
{conversation_text}

Instructions:
- Analyze the conversation content carefully
- Only apply tags where the conversation clearly contains the described content
- If a tag's description doesn't match the conversation, don't include it
- Return only the tag names that match, one per line
- If no tags match, return nothing

Matching tag names:"""
        
        try:
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            if not result_text:
                return []
            
            # Parse the response to extract tag names
            suggested_tags = []
            for line in result_text.split('\n'):
                tag_name = line.strip()
                if tag_name and any(config.name == tag_name for config in self.tag_configs):
                    suggested_tags.append(tag_name)
            
            return suggested_tags
            
        except Exception as e:
            print(f"Warning: Failed to evaluate tags using Gemini API: {e}")
            return []
    
    def _sample_conversation_content(self, conversation_content: List[str], max_messages: int) -> str:
        """
        Sample conversation content to represent the entire conversation.
        Uses the same strategy as FilenameGenerator for consistency.
        """
        if len(conversation_content) <= max_messages:
            return "\n".join(conversation_content)
        
        # For longer conversations, use stratified sampling
        total_messages = len(conversation_content)
        
        # Always include first few messages (conversation start)
        start_count = min(10, max_messages // 4)
        sampled_messages = conversation_content[:start_count]
        remaining_quota = max_messages - start_count
        
        # Always include last few messages (conversation end)
        end_count = min(10, remaining_quota // 3)
        sampled_messages.extend(conversation_content[-end_count:])
        remaining_quota -= end_count
        
        # Sample from the middle portion
        middle_start = start_count
        middle_end = total_messages - end_count
        
        if middle_end > middle_start and remaining_quota > 0:
            middle_messages = conversation_content[middle_start:middle_end]
            
            if len(middle_messages) <= remaining_quota:
                # Include all middle messages if they fit
                sampled_messages[start_count:start_count] = middle_messages
            else:
                # Evenly sample from middle portion
                step = len(middle_messages) / remaining_quota
                indices = [int(i * step) for i in range(remaining_quota)]
                middle_sampled = [middle_messages[i] for i in indices]
                sampled_messages[start_count:start_count] = middle_sampled
        
        # Add separator comments to show where content was sampled from
        result = []
        result.extend(sampled_messages[:start_count])
        
        if remaining_quota > 0 and middle_end > middle_start:
            result.append("... [conversation continues] ...")
            result.extend(sampled_messages[start_count:-end_count])
        
        if end_count > 0:
            result.append("... [end of conversation] ...")
            result.extend(sampled_messages[-end_count:])
        
        return "\n".join(result)
    
    def map_participants(self, aim_handles: List[str]) -> List[str]:
        """
        Map AIM handles to markdown participant links.
        
        Args:
            aim_handles: List of AIM username handles
            
        Returns:
            List of markdown links for participants, falling back to AIM handle if no mapping found
        """
        mapped_participants = []
        
        for handle in aim_handles:
            # Find matching participant config
            participant_config = None
            for config in self.participant_configs:
                if config.aim == handle:
                    participant_config = config
                    break
            
            if participant_config:
                # Use markdown link from config
                mapped_participants.append(participant_config.md)
            else:
                # Fall back to AIM handle
                mapped_participants.append(handle)
        
        return mapped_participants
    
    def get_human_readable_names(self, aim_handles: List[str]) -> Dict[str, str]:
        """
        Get mapping from AIM handles to human-readable names.
        
        Args:
            aim_handles: List of AIM username handles
            
        Returns:
            Dictionary mapping AIM handle to human-readable name (or handle if no mapping)
        """
        name_mapping = {}
        
        for handle in aim_handles:
            # Find matching participant config
            participant_config = None
            for config in self.participant_configs:
                if config.aim == handle:
                    participant_config = config
                    break
            
            if participant_config:
                # Use human-readable name from config
                name_mapping[handle] = participant_config.name
            else:
                # Fall back to AIM handle
                name_mapping[handle] = handle
        
        return name_mapping