from datetime import datetime, time
from typing import List, Optional
import re
from src.aim_parser import Message


class MarkdownConverter:
    def __init__(self):
        # Characters that need to be escaped in Markdown (minimal set for blockquotes)
        self.escape_chars = ['*', '_', '`', '[', ']']
        # Grouping threshold in minutes
        self.group_threshold_minutes = 2
    
    def convert(self, messages: List[Message], conversation_date: Optional[datetime] = None, 
                group_consecutive: bool = True, description: Optional[str] = None, 
                tags: Optional[List[str]] = None) -> str:
        if not messages:
            return ""
        
        output = []
        
        # Add frontmatter if date is provided
        if conversation_date:
            date_str = conversation_date.strftime("%Y-%m-%d")
            output.append("---")
            output.append(f"date: {date_str}")
            if description:
                output.append(f"description: {description}")
            
            # Add tags (default to aim if none provided or empty)
            tags_to_use = tags if tags else ["aim"]
            output.append("tags:")
            for tag in tags_to_use:
                output.append(f"  - {tag}")
            
            output.append("---")
        
        # Add header if date is provided
        if conversation_date:
            date_str = conversation_date.strftime("%B %d, %Y")
            output.append(f"# AIM Conversation - {date_str}\n")
        
        # Convert messages with improved grouping
        previous_sender = None
        previous_timestamp = None
        current_group_messages = []
        
        def flush_group():
            """Flush the current group of messages to output."""
            if not current_group_messages:
                return
            
            # Add sender and timestamp for the first message in group
            first_msg = current_group_messages[0]
            output.append(f"**{first_msg.sender}** ({first_msg.timestamp}):")
            
            # Add all message contents without individual timestamps
            for msg in current_group_messages:
                content_lines = msg.content.split('\n')
                for line in content_lines:
                    escaped_line = self._escape_markdown(line)
                    output.append(f"> {escaped_line}")
            
            # Empty line after group
            output.append("")
            current_group_messages.clear()
        
        for message in messages:
            if message.is_system_message:
                # Flush any pending group before system message
                flush_group()
                if message.is_auto_response:
                    # Format auto response as QUOTE callout
                    output.append(f"> [!QUOTE] Auto response from {message.sender} ({message.timestamp})")
                    # Handle multiline content by prefixing each line with >
                    content_lines = message.content.split('\n')
                    for line in content_lines:
                        escaped_line = self._escape_markdown(line)
                        output.append(f"> {escaped_line}")
                elif message.is_session_concluded:
                    # Format session concluded as ATTENTION callout
                    output.append(f"> [!ATTENTION]\n> {message.content}")
                else:
                    # Regular system message as NOTE callout
                    output.append(f"> [!NOTE]\n> {message.content}")
                output.append("")
                previous_sender = None
                previous_timestamp = None
            else:
                current_time = self._parse_timestamp(message.timestamp)
                should_start_new_group = False
                
                if not group_consecutive:
                    # No grouping - treat each message separately
                    should_start_new_group = True
                elif previous_sender != message.sender:
                    # Different sender - always start new group
                    should_start_new_group = True
                elif previous_timestamp is None or current_time is None:
                    # Can't parse timestamp - start new group to be safe
                    should_start_new_group = True
                else:
                    # Same sender - check time threshold
                    time_diff = self._time_diff_minutes(previous_timestamp, current_time)
                    if time_diff > self.group_threshold_minutes:
                        should_start_new_group = True
                
                if should_start_new_group:
                    # Flush current group and start new one
                    flush_group()
                
                # Add message to current group
                current_group_messages.append(message)
                previous_sender = message.sender
                previous_timestamp = current_time
        
        # Flush any remaining group
        flush_group()
        
        return '\n'.join(output)
    
    def _parse_timestamp(self, timestamp_str: str) -> Optional[time]:
        """Parse AIM timestamp string (e.g., '10:57:26 PM') into a time object."""
        try:
            # Handle format like "10:57:26 PM" or "10:57 PM"
            timestamp_str = timestamp_str.strip()
            if re.match(r'\d{1,2}:\d{2}:\d{2} [AP]M', timestamp_str):
                return datetime.strptime(timestamp_str, '%I:%M:%S %p').time()
            elif re.match(r'\d{1,2}:\d{2} [AP]M', timestamp_str):
                return datetime.strptime(timestamp_str, '%I:%M %p').time()
        except ValueError:
            pass
        return None
    
    def _time_diff_minutes(self, time1: time, time2: time) -> float:
        """Calculate difference in minutes between two time objects."""
        # Convert times to minutes since midnight
        minutes1 = time1.hour * 60 + time1.minute + time1.second / 60.0
        minutes2 = time2.hour * 60 + time2.minute + time2.second / 60.0
        
        diff = abs(minutes2 - minutes1)
        # Handle day boundary crossing (e.g., 11:59 PM to 12:01 AM)
        if diff > 12 * 60:  # More than 12 hours suggests day boundary
            diff = 24 * 60 - diff
        
        return diff
    
    def _escape_markdown(self, text: str) -> str:
        # Escape special Markdown characters
        for char in self.escape_chars:
            text = text.replace(char, f'\\{char}')
        return text