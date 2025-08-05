import os
import re
from datetime import datetime
from typing import List, Set
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
    
    def generate_filename(self, messages: List[Message], conversation_date: datetime = None) -> str:
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
        title = self._generate_title_with_llm(messages)
        
        # Sanitize the title for filename use
        title = self._sanitize_title(title)
        
        return f"{date_str} {title} {participants_str}"
    
    def generate_description(self, messages: List[Message]) -> str:
        """Generate a conversation description using Gemini API"""
        if not messages:
            return "Empty conversation"
        
        # Filter out system messages for description generation
        regular_messages = [msg for msg in messages if not msg.is_system_message]
        if not regular_messages:
            return "Conversation with only system messages"
        
        # Prepare conversation content for the LLM (similar to title generation)
        conversation_content = []
        for message in regular_messages:
            conversation_content.append(f"{message.sender}: {message.content}")
        
        # Limit content to avoid token limits (take first 30 messages for description)
        if len(conversation_content) > 30:
            conversation_content = conversation_content[:30]
        
        conversation_text = "\n".join(conversation_content)
        
        prompt = f"""Based on this AIM conversation, generate a concise description (1-2 sentences) that summarizes the main topics, themes, and key events discussed. This description will be used by other LLMs to quickly understand whether the conversation is relevant to their search criteria.

Focus on:
- Main topics or subjects discussed
- Key events mentioned
- Overall themes or purposes of the conversation
- Important decisions or conclusions reached

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
    
    def _generate_title_with_llm(self, messages: List[Message]) -> str:
        """Generate a descriptive title using Gemini API"""
        if not messages:
            return "Conversation"
        
        # Prepare conversation content for the LLM
        conversation_content = []
        for message in messages:
            if not message.is_system_message:
                conversation_content.append(f"{message.sender}: {message.content}")
        
        # Limit content to avoid token limits (take first 20 messages)
        if len(conversation_content) > 20:
            conversation_content = conversation_content[:20]
        
        conversation_text = "\n".join(conversation_content)
        
        prompt = f"""Based on this AIM conversation, generate a concise, descriptive title (3-6 words) that captures the main topic or theme of the conversation. The title should be suitable for a filename.

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
    
    def _sanitize_title(self, title: str) -> str:
        """Sanitize title for filename compatibility"""
        # Replace problematic characters with spaces or remove them
        sanitized = re.sub(r'[<>:"/\\|?*]', ' ', title)
        # Replace multiple spaces with single space
        sanitized = re.sub(r'\s+', ' ', sanitized)
        # Remove leading/trailing spaces
        sanitized = sanitized.strip()
        return sanitized