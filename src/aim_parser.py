import re
import html
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Message:
    sender: str
    timestamp: str
    content: str
    is_system_message: bool = False


class AIMParser:
    def __init__(self):
        self.message_pattern = re.compile(
            r'<B>.*?<FONT[^>]*>([^<]+)<!-- \(([^)]+)\)--></B>.*?</FONT>.*?<FONT[^>]*>([^<]+(?:<BR>\s*)?)</FONT>',
            re.DOTALL
        )
        self.sign_off_pattern = re.compile(
            r'<B><FONT[^>]*>([^<]+signed off at[^<]+)</B>\.?</FONT>',
            re.DOTALL
        )
    
    def parse(self, html_content: str) -> List[Message]:
        messages = []
        
        # Split by line breaks, but keep track of multiline messages
        lines = html_content.split('<BR>')
        current_message_html = ""
        
        for i, line in enumerate(lines):
            if not line.strip():
                continue
                
            # Check if this line starts a new message (has timestamp)
            has_timestamp = '<!-- (' in line and ')-->' in line
            
            if has_timestamp and current_message_html:
                # Process the previous message
                self._process_message_line(current_message_html, messages)
                current_message_html = line
            else:
                # Continue building the current message
                current_message_html += line
        
        # Process the last message
        if current_message_html:
            self._process_message_line(current_message_html, messages)
        
        return messages
    
    def _process_message_line(self, line: str, messages: List[Message]):
        # Check if this is a sign-off message
        if 'signed off at' in line:
            sign_off_match = re.search(r'([^>]+signed off at[^<]+)', line)
            if sign_off_match:
                messages.append(Message(
                    sender="System",
                    timestamp="",
                    content=sign_off_match.group(1).strip(),
                    is_system_message=True
                ))
                return
        
        # Extract sender and timestamp
        sender_match = re.search(r'<B>.*?<FONT[^>]*>([^<]+)<!-- \(([^)]+)\)--></B>', line)
        if not sender_match:
            return
            
        sender = sender_match.group(1).strip()
        timestamp = sender_match.group(2).strip()
        
        # Find all FONT tags after the sender info
        sender_end = line.find('</B>')
        if sender_end == -1:
            return
            
        content_part = line[sender_end:]
        
        # Extract all text from FONT tags, including nested content
        # Use a more comprehensive pattern that handles multiline content
        font_pattern = r'<FONT[^>]*>(.*?)</FONT>'
        font_matches = re.findall(font_pattern, content_part, re.DOTALL)
        
        # Combine all the content, filtering out formatting tags
        combined_content = ""
        for match in font_matches:
            # Remove nested tags like <I>
            clean_match = re.sub(r'<[^>]+>', '', match)
            combined_content += clean_match
        
        # Now process the combined content
        # Remove special standalone characters at the beginning
        combined_content = re.sub(r'^[:\s]+', '', combined_content)
        
        if combined_content.strip():
            # Handle HTML entities
            full_content = html.unescape(combined_content)
            # Clean up whitespace - normalize newlines to single spaces
            full_content = re.sub(r'\s*\n\s*', ' ', full_content)
            # Don't collapse multiple spaces - just clean up excessive ones (3+ spaces)
            full_content = re.sub(r'   +', '  ', full_content)
            full_content = full_content.strip()
            
            messages.append(Message(
                sender=sender,
                timestamp=timestamp,
                content=full_content,
                is_system_message=False
            ))
    
    def extract_date_from_filename(self, filename: str) -> datetime:
        # Extract date from filename format "2004-05-18 [Tuesday].htm"
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
        if date_match:
            date_str = date_match.group(1)
            return datetime.strptime(date_str, '%Y-%m-%d')
        raise ValueError(f"Could not extract date from filename: {filename}")