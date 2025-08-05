import re
import html
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional
from abc import ABC, abstractmethod


@dataclass
class Message:
    sender: str
    timestamp: str
    content: str
    is_system_message: bool = False


class BaseAIMParser(ABC):
    """Base class for AIM conversation parsers"""
    
    @abstractmethod
    def can_parse(self, html_content: str) -> bool:
        """Check if this parser can handle the given HTML format"""
        pass
    
    @abstractmethod
    def parse(self, html_content: str) -> List[Message]:
        """Parse the HTML content and return messages"""
        pass
    
    def extract_date_from_filename(self, filename: str) -> datetime:
        """Extract date from filename format "2004-05-18 [Tuesday].htm" """
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
        if date_match:
            date_str = date_match.group(1)
            return datetime.strptime(date_str, '%Y-%m-%d')
        raise ValueError(f"Could not extract date from filename: {filename}")


class CommentBasedParser(BaseAIMParser):
    """Parser for AIM format that uses HTML comments for timestamps"""
    
    def __init__(self):
        self.message_pattern = re.compile(
            r'<B>.*?<FONT[^>]*>([^<]+)<!-- \(([^)]+)\)--></B>.*?</FONT>.*?<FONT[^>]*>([^<]+(?:<BR>\s*)?)</FONT>',
            re.DOTALL
        )
        self.sign_off_pattern = re.compile(
            r'<B><FONT[^>]*>([^<]+signed off at[^<]+)</B>\.?</FONT>',
            re.DOTALL
        )
    
    def can_parse(self, html_content: str) -> bool:
        """Check if this HTML uses comment-based timestamps"""
        return '<!-- (' in html_content and ')-->' in html_content
    
    def parse(self, html_content: str) -> List[Message]:
        """Parse comment-based AIM format"""
        messages = []
        
        # Split by line breaks and process messages
        lines = html_content.split('<BR>')
        current_message_html = ""
        
        for line in lines:
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
        """Process a single message line from comment-based format"""
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
        
        # Extract sender and timestamp using comment format
        sender_match = re.search(r'<B>.*?<FONT[^>]*>([^<]+)<!-- \(([^)]+)\)--></B>', line)
        if not sender_match:
            return
            
        sender = sender_match.group(1).strip()
        timestamp = sender_match.group(2).strip()
        
        # Extract content - find FONT tags after the sender
        sender_end = line.find('</B>')
        if sender_end == -1:
            return
            
        content_part = line[sender_end:]
        font_pattern = r'<FONT[^>]*>(.*?)</FONT>'
        font_matches = re.findall(font_pattern, content_part, re.DOTALL)
        
        combined_content = ""
        for match in font_matches:
            clean_match = re.sub(r'<[^>]+>', '', match)
            combined_content += clean_match
        
        # Clean up content
        combined_content = re.sub(r'^[:\s]+', '', combined_content)
        
        if combined_content.strip():
            # Handle HTML entities and cleanup
            full_content = html.unescape(combined_content)
            full_content = re.sub(r'\s*\n\s*', ' ', full_content)
            full_content = re.sub(r'   +', '  ', full_content)
            full_content = full_content.strip()
            
            messages.append(Message(
                sender=sender,
                timestamp=timestamp,
                content=full_content,
                is_system_message=False
            ))


class SpanBasedParser(BaseAIMParser):
    """Parser for AIM format that uses SPAN tags with nested timestamp SPANs"""
    
    def __init__(self):
        # Pattern for SPAN-based timestamps
        self.span_message_pattern = re.compile(
            r'<B><FONT[^>]*>([^<]+)<SPAN[^>]*>\s*\(([^)]+)\)</SPAN></B></FONT>',
            re.DOTALL
        )
        self.sign_off_pattern = re.compile(
            r'<B><FONT[^>]*>([^<]+signed off at[^<]+)</B>\.?</FONT>',
            re.DOTALL
        )
    
    def can_parse(self, html_content: str) -> bool:
        """Check if this HTML uses SPAN-based format with background-color"""
        return '<SPAN STYLE="background-color: #ffffff;">' in html_content
    
    def parse(self, html_content: str) -> List[Message]:
        """Parse SPAN-based AIM format"""
        messages = []
        
        # Each message is wrapped in a SPAN with background-color
        # Split by these SPAN tags and process each one
        parts = html_content.split('<SPAN STYLE="background-color: #ffffff;">')
        
        for i, part in enumerate(parts[1:]):  # Skip the first empty part
            # Find the end of this SPAN message
            span_end = self._find_span_end(part)
            if span_end == -1:
                continue
                
            message_content = part[:span_end]
            self._process_span_message(message_content, messages)
        return messages
    
    def _find_span_end(self, content: str) -> int:
        """Find the end of a SPAN message, handling nested SPANs"""
        span_count = 1
        i = 0
        
        while i < len(content) and span_count > 0:
            if content[i:i+5] == '<SPAN':
                span_count += 1
                # Skip to end of tag
                tag_end = content.find('>', i)
                i = tag_end + 1 if tag_end != -1 else i + 1
            elif content[i:i+7] == '</SPAN>':
                span_count -= 1
                if span_count == 0:
                    return i
                i += 7
            else:
                i += 1
        
        return -1 if span_count > 0 else i
    
    def _process_span_message(self, message_html: str, messages: List[Message]):
        """Process a single SPAN message"""
        # Check if this is a sign-off message
        if 'signed off at' in message_html:
            sign_off_match = re.search(r'([^>]+signed off at[^<]+)', message_html)
            if sign_off_match:
                messages.append(Message(
                    sender="System",
                    timestamp="",
                    content=sign_off_match.group(1).strip(),
                    is_system_message=True
                ))
                return
        
        # Extract sender and timestamp using SPAN pattern
        # Try multiple patterns to handle different HTML formats
        sender_match = None
        
        # Pattern 1: <B><FONT>sender<SPAN>(timestamp)</SPAN></B></FONT>
        sender_match = re.search(r'<B><FONT[^>]*>([^<]+)<SPAN[^>]*>\s*\(([^)]+)\)</SPAN></B>:?</FONT>', message_html)
        
        # Pattern 2: <FONT>sender<SPAN>(timestamp)</SPAN></B></FONT> (B tag after sender)
        if not sender_match:
            sender_match = re.search(r'<FONT[^>]*>([^<]+)<SPAN[^>]*>\s*\(([^)]+)\)</SPAN></B>:?</FONT>', message_html)
        
        if not sender_match:
            return
            
        sender = sender_match.group(1).strip()
        timestamp = sender_match.group(2).strip()
        
        # Extract message content
        # Look for content after the sender/timestamp structure
        # Pattern: </B></FONT>...<FONT>actual content</FONT>
        content = self._extract_message_content(message_html)
        
        if content:
            messages.append(Message(
                sender=sender,
                timestamp=timestamp,
                content=content,
                is_system_message=False
            ))
    
    def _extract_message_content(self, message_html: str) -> str:
        """Extract the actual message content from SPAN format"""
        # Find all FONT tags and their content
        font_pattern = r'<FONT[^>]*>([^<]*(?:<[^/][^>]*>[^<]*)*?)</FONT>'
        font_matches = re.findall(font_pattern, message_html, re.DOTALL)
        
        # The message content is typically in FONT tags after the sender block
        # Skip FONT tags that are part of the sender/timestamp or just contain ":"
        for match in font_matches:
            # Remove nested tags
            clean_text = re.sub(r'<[^>]+>', '', match).strip()
            
            # Skip if it's empty, just a colon, or looks like timestamp info
            if (clean_text and 
                clean_text != ':' and 
                '(' not in clean_text and 
                ')' not in clean_text and
                'SPAN' not in match and  # Skip if it contains nested SPAN
                len(clean_text) > 1):
                # Clean up HTML entities and whitespace
                content = html.unescape(clean_text)
                content = re.sub(r'\s*\n\s*', ' ', content)
                content = re.sub(r'   +', '  ', content)
                return content.strip()
        
        return ""


class AIMParserFactory:
    """Factory class to select the appropriate parser for AIM formats"""
    
    @staticmethod
    def get_parser(html_content: str) -> BaseAIMParser:
        """Get the appropriate parser for the given HTML content"""
        # Try parsers in order of preference/specificity
        # SpanBasedParser first as it's more specific
        parser_classes = [SpanBasedParser, CommentBasedParser]
        
        for parser_class in parser_classes:
            parser = parser_class()
            if parser.can_parse(html_content):
                return parser
        
        # Fallback to comment-based parser if no specific match
        return CommentBasedParser()


class AIMParser:
    """Main AIM parser that uses factory pattern to delegate to format-specific parsers"""
    
    def __init__(self):
        self.factory = AIMParserFactory()
    
    def parse(self, html_content: str) -> List[Message]:
        """Parse AIM HTML content using appropriate format-specific parser"""
        parser = self.factory.get_parser(html_content)
        return parser.parse(html_content)
    
    def extract_date_from_filename(self, filename: str) -> datetime:
        """Extract date from filename - delegates to base parser method"""
        # Use any parser instance for this utility method
        parser = CommentBasedParser()
        return parser.extract_date_from_filename(filename)