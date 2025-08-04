from datetime import datetime
from typing import List, Optional
from src.aim_parser import Message


class MarkdownConverter:
    def __init__(self):
        # Characters that need to be escaped in Markdown
        self.escape_chars = ['*', '_', '`', '[', ']', '(', ')', '#', '+', '-', '.', '!']
    
    def convert(self, messages: List[Message], conversation_date: Optional[datetime] = None, 
                group_consecutive: bool = False) -> str:
        if not messages:
            return ""
        
        output = []
        
        # Add header if date is provided
        if conversation_date:
            date_str = conversation_date.strftime("%B %d, %Y")
            output.append(f"# AIM Conversation - {date_str}\n")
        
        # Convert messages
        previous_sender = None
        for message in messages:
            if message.is_system_message:
                output.append(f"*[System: {message.content}]*")
            else:
                # Check if we should show full sender info or just timestamp
                if group_consecutive and previous_sender == message.sender:
                    # Just show timestamp for consecutive messages from same sender
                    output.append(f"({message.timestamp}):")
                else:
                    # Show full sender info
                    output.append(f"**{message.sender}** ({message.timestamp}):")
                    previous_sender = message.sender
                
                # Format the message content
                content_lines = message.content.split('\n')
                for line in content_lines:
                    escaped_line = self._escape_markdown(line)
                    output.append(f"> {escaped_line}")
            
            # Empty line after each message/block
            output.append("")
        
        return '\n'.join(output)
    
    def _escape_markdown(self, text: str) -> str:
        # Escape special Markdown characters
        for char in self.escape_chars:
            text = text.replace(char, f'\\{char}')
        return text