import os
import re
from datetime import datetime
from typing import List, Set, Dict
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv
from src.aim_parser import Message


class FilenameGenerator:
    def __init__(self):
        # Load environment variables from .env file
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
    
    def generate_filename(self, messages: List[Message], conversation_date: datetime = None, name_mapping: Dict[str, str] = None) -> str:
        """Generate a standardized filename in format: YYYY-MM-DD Title [user1, user2]"""
        # Get date
        if conversation_date:
            date_str = conversation_date.strftime("%Y-%m-%d")
        else:
            date_str = datetime.now().strftime("%Y-%m-%d")
        
        # Get participants
        participants = self._extract_participants(messages)
        participants_str = f"[{', '.join(sorted(participants))}]"
        
        # Generate title using Gemini
        title = self._generate_title_with_llm(messages, name_mapping)
        
        # Sanitize the title for filename use
        title = self._sanitize_title(title)
        
        return f"{date_str} {title} {participants_str}"
    
    def generate_description(self, messages: List[Message], name_mapping: Dict[str, str] = None) -> str:
        """Generate a conversation description using Gemini API"""
        if not messages:
            return "Empty conversation"
        
        # Filter out system messages for description generation
        regular_messages = [msg for msg in messages if not msg.is_system_message]
        if not regular_messages:
            return "Conversation with only system messages"
        
        # Prepare conversation content for the LLM
        conversation_content = []
        for message in regular_messages:
            # Use human-readable name if mapping is provided, otherwise use original sender
            display_name = name_mapping.get(message.sender, message.sender) if name_mapping else message.sender
            conversation_content.append(f"{display_name}: {message.content}")
        
        # Use smart sampling to represent entire conversation while staying within reasonable limits
        conversation_text = self._sample_conversation_content(conversation_content, max_messages=100)
        
        prompt = f"""Based on this AIM conversation, generate a concise description (1-2 sentences) that summarizes the main topics, themes, and key events discussed throughout the ENTIRE conversation. This description will be used by other LLMs to quickly understand whether the conversation is relevant to their search criteria.

IMPORTANT: Pay attention to the full conversation flow from beginning to end. If the conversation sample includes separator markers like "... [conversation continues] ..." or "... [end of conversation] ...", ensure you consider themes and topics from all parts of the conversation, not just the beginning.

Focus on:
- Main topics or subjects discussed throughout the conversation
- Key events mentioned at any point
- Overall themes or purposes that emerge across the full conversation
- Important decisions or conclusions reached (especially near the end)
- Evolution of topics from start to finish

Conversation:
{conversation_text}

Examples of good descriptions:
- "In this conversation Bob and Alice discuss planning their summer vacation to Italy, comparing flight options and hotel recommendations before deciding on travel dates."
- "Alice and Bob catch up after a long time apart, sharing updates about their jobs, discussing mutual friends, and making plans to meet up next weekend."
- "The conversation focuses on troubleshooting a software bug, with Bob helping Alice debug her Python code and suggesting alternative approaches to the problem."

Generate only the description, nothing else:"""

        try:
            response = self.model.generate_content(prompt)
            description = response.text.strip()
            
            # Clean up the response
            description = re.sub(r'^["\']|["\']$', '', description)  # Remove quotes
            description = description.replace('\n', ' ').strip()
            
            # Ensure reasonable length (not too short or too long)
            if len(description) < 20:
                return "Brief conversation between participants"
            elif len(description) > 300:
                description = description[:300].strip()
                # Try to end at a complete sentence
                last_period = description.rfind('.')
                if last_period > 200:
                    description = description[:last_period + 1]
                
            return description if description else "General conversation between participants"
            
        except Exception as e:
            raise RuntimeError(f"Failed to generate description using Gemini API: {e}")
    
    def _extract_participants(self, messages: List[Message]) -> Set[str]:
        """Extract unique participant names from messages"""
        participants = set()
        for message in messages:
            if not message.is_system_message and message.sender:
                participants.add(message.sender)
        return participants
    
    def _generate_title_with_llm(self, messages: List[Message], name_mapping: Dict[str, str] = None) -> str:
        """Generate a descriptive title using Gemini API"""
        if not messages:
            return "Conversation"
        
        # Prepare conversation content for the LLM
        conversation_content = []
        for message in messages:
            if not message.is_system_message:
                # Use human-readable name if mapping is provided, otherwise use original sender
                display_name = name_mapping.get(message.sender, message.sender) if name_mapping else message.sender
                conversation_content.append(f"{display_name}: {message.content}")
        
        # Use smart sampling to represent entire conversation while staying within reasonable limits
        conversation_text = self._sample_conversation_content(conversation_content, max_messages=100)
        
        prompt = f"""Based on this AIM conversation, generate a concise, descriptive title (3-6 words) that captures the main topic or theme discussed throughout the ENTIRE conversation. The title should be suitable for a filename.

IMPORTANT: Consider the full conversation flow from beginning to end. If the conversation sample includes separator markers like "... [conversation continues] ..." or "... [end of conversation] ...", make sure your title reflects the overall theme or most significant topic discussed across all parts of the conversation, not just the opening messages.

Conversation:
{conversation_text}

Examples of good titles:
- "Planning first trip to beach"
- "Birthday wishes for Alice" 
- "Catching up during COVID lockdown"
- "Gaming session discussion"
- "Weekend dinner plans"

Generate only the title, nothing else:"""

        try:
            response = self.model.generate_content(prompt)
            title = response.text.strip()
            
            # Clean up the response in case it includes extra formatting
            title = re.sub(r'^["\']|["\']$', '', title)  # Remove quotes
            title = title.replace('\n', ' ').strip()
            
            # Ensure it's not too long
            if len(title) > 50:
                title = title[:50].strip()
                
            return title if title else "General conversation"
            
        except Exception as e:
            raise RuntimeError(f"Failed to generate title using Gemini API: {e}")
    
    def _sample_conversation_content(self, conversation_content: List[str], max_messages: int) -> str:
        """
        Intelligently sample conversation content to represent the entire conversation.
        Uses stratified sampling to ensure coverage across the full conversation.
        """
        if len(conversation_content) <= max_messages:
            # If conversation is short enough, use all messages
            return "\n".join(conversation_content)
        
        # For longer conversations, use stratified sampling
        # Divide conversation into segments and sample from each
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
    
    def _sanitize_title(self, title: str) -> str:
        """Sanitize title for filename compatibility"""
        # Replace problematic characters with spaces or remove them
        sanitized = re.sub(r'[<>:"/\\|?*]', ' ', title)
        # Replace multiple spaces with single space
        sanitized = re.sub(r'\s+', ' ', sanitized)
        # Remove leading/trailing spaces
        sanitized = sanitized.strip()
        return sanitized