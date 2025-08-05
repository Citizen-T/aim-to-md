import unittest
from datetime import datetime
from src.aim_parser import AIMParser, Message, AIMParserFactory, CommentBasedParser, SpanBasedParser


class TestAIMParser(unittest.TestCase):
    def setUp(self):
        self.parser = AIMParser()
    
    def test_parse_single_message(self):
        html_content = '''<B><FONT COLOR="#0000ff" LANG="0">UserA<!-- (10:56:59 PM)--></B></FONT><FONT COLOR="#0000ff" BACK="#ffffff">:</FONT><FONT COLOR="#000000"> </FONT><FONT FACE="Arial" SIZE=2>hello</FONT><BR>'''
        
        messages = self.parser.parse(html_content)
        
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].sender, "UserA")
        self.assertEqual(messages[0].timestamp, "10:56:59 PM")
        self.assertEqual(messages[0].content, "hello")
    
    def test_parse_multiple_messages(self):
        html_content = '''<B><FONT COLOR="#0000ff" LANG="0">UserA<!-- (10:56:59 PM)--></B></FONT><FONT COLOR="#0000ff" BACK="#ffffff">:</FONT><FONT COLOR="#000000"> </FONT><FONT FACE="Arial" SIZE=2>hello</FONT><BR>
<B><FONT COLOR="#ff0000" FACE="Times New Roman" SIZE=3>UserB<!-- (10:57:05 PM)--></B>:</FONT><FONT COLOR="#000000"> <I></FONT><FONT COLOR="#0080ff" FACE="Tubular" SIZE=2>hi there</FONT><BR>'''
        
        messages = self.parser.parse(html_content)
        
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].sender, "UserA")
        self.assertEqual(messages[0].content, "hello")
        self.assertEqual(messages[1].sender, "UserB")
        self.assertEqual(messages[1].content, "hi there")
    
    def test_parse_message_with_quotes(self):
        html_content = '''<B><FONT COLOR="#ff0000" FACE="Times New Roman" SIZE=3>UserB<!-- (10:57:43 PM)--></B>:</FONT><FONT COLOR="#000000"> <I></FONT><FONT COLOR="#0080ff" FACE="Tubular" SIZE=2>&quot;what time is it?&quot;</FONT><BR>'''
        
        messages = self.parser.parse(html_content)
        
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].content, '"what time is it?"')
    
    def test_parse_multiline_message(self):
        html_content = '''<B><FONT COLOR="#0000ff" FACE="Times New Roman" SIZE=3>UserC<!-- (10:58:27 PM)--></B>:</FONT><FONT COLOR="#000000"> </FONT><FONT FACE="Arial" SIZE=2>hey did you see that new episode last night
it was really good</FONT><BR>'''
        
        messages = self.parser.parse(html_content)
        
        self.assertEqual(len(messages), 1)
        expected_content = "hey did you see that new episode last night it was really good"
        self.assertEqual(messages[0].content, expected_content)
    
    def test_parse_html_entities(self):
        html_content = '''<B><FONT COLOR="#ff0000" FACE="Times New Roman" SIZE=3>UserD<!-- (11:39:10 PM)--></B>:</FONT><FONT COLOR="#000000"> <I></FONT><FONT COLOR="#0080ff" FACE="Tubular" SIZE=2>GameUser123:  someone said &quot; 
make sure to be there on time tomorrow&quot;<BR>
</FONT><BR>'''
        
        messages = self.parser.parse(html_content)
        
        self.assertEqual(len(messages), 1)
        expected_content = 'GameUser123:  someone said " make sure to be there on time tomorrow"'
        self.assertEqual(messages[0].content, expected_content)
    
    def test_extract_date_from_filename(self):
        filename = "2004-05-18 [Tuesday].htm"
        
        date = self.parser.extract_date_from_filename(filename)
        
        self.assertEqual(date, datetime(2004, 5, 18))
    
    def test_parse_sign_off_message(self):
        html_content = '''<B><FONT COLOR="#0000ff" FACE="Times New Roman" SIZE=3>UserA signed off at 12:28:30 AM</B>.</FONT>'''
        
        messages = self.parser.parse(html_content)
        
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].sender, "System")
        self.assertEqual(messages[0].content, "UserA signed off at 12:28:30 AM")
        self.assertTrue(messages[0].is_system_message)
    
    def test_parse_span_timestamp_format(self):
        """Test parsing messages with SPAN-based timestamp format"""
        html_content = '''<SPAN STYLE="background-color: #ffffff;"><B><FONT COLOR="#0000ff" LANG="0">Bob<SPAN STYLE="font-size: xx-small;"> (10:54:39 PM)</SPAN></B></FONT><FONT COLOR="#0000ff" SIZE="2" LANG="0">: </FONT><FONT SIZE="2" LANG="0">hey</FONT></SPAN><BR>
<SPAN STYLE="background-color: #ffffff;"><B><FONT COLOR="#ff0000" LANG="0">AliceTest<SPAN STYLE="font-size: xx-small;"> (10:54:42 PM)</SPAN></B></FONT><FONT COLOR="#ff0000" SIZE="2" LANG="0">: </FONT><FONT SIZE="2" LANG="0">hello there</FONT></SPAN><BR>'''
        
        messages = self.parser.parse(html_content)
        
        self.assertEqual(len(messages), 2)
        
        self.assertEqual(messages[0].sender, "Bob")
        self.assertEqual(messages[0].timestamp, "10:54:39 PM")
        self.assertEqual(messages[0].content, "hey")
        
        self.assertEqual(messages[1].sender, "AliceTest")
        self.assertEqual(messages[1].timestamp, "10:54:42 PM")
        self.assertEqual(messages[1].content, "hello there")
    
    def test_parse_mixed_timestamp_formats(self):
        """Test parsing messages with both comment and SPAN timestamp formats"""
        # This test expects each parser to handle its own format
        # The factory will choose the appropriate parser
        comment_html = '''<B><FONT COLOR="#0000ff">Alice<!-- (10:57:26 PM)--></B></FONT>: <FONT>Hey there!</FONT><BR>'''
        span_html = '''<SPAN STYLE="background-color: #ffffff;"><B><FONT COLOR="#ff0000" LANG="0">Bob<SPAN STYLE="font-size: xx-small;"> (10:57:30 PM)</SPAN></B></FONT><FONT COLOR="#ff0000" SIZE="2" LANG="0">: </FONT><FONT SIZE="2" LANG="0">Hi Alice!</FONT></SPAN><BR>'''
        
        # Test comment format
        comment_messages = self.parser.parse(comment_html)
        self.assertEqual(len(comment_messages), 1)
        self.assertEqual(comment_messages[0].sender, "Alice")
        self.assertEqual(comment_messages[0].content, "Hey there!")
        
        # Test SPAN format
        span_messages = self.parser.parse(span_html)
        self.assertEqual(len(span_messages), 1)
        self.assertEqual(span_messages[0].sender, "Bob")
        self.assertEqual(span_messages[0].content, "Hi Alice!")
    
    def test_parse_span_format_variant_with_b_after_sender(self):
        """Test parsing SPAN format where <B> tag comes after sender name"""
        # This tests the second pattern we discovered: <FONT>sender<SPAN>(timestamp)</SPAN></B></FONT>
        html_content = '''<SPAN STYLE="background-color: #ffffff;"><FONT COLOR="#0000ff" FACE="Times New Roman">Alice2<SPAN STYLE="font-size: xx-small;"> (9:29:26 PM)</SPAN></B>:</FONT><FONT COLOR="#000000"> ::sigh::</FONT><BR></SPAN>
<SPAN STYLE="background-color: #ffffff;"><FONT COLOR="#ff0000" FACE="Times New Roman">Bob2<SPAN STYLE="font-size: xx-small;"> (9:29:48 PM)</SPAN></B>:</FONT><FONT COLOR="#000000"> <B></FONT><FONT COLOR="#008040" FACE="Perpetua">do I?</FONT><BR></SPAN>'''
        
        messages = self.parser.parse(html_content)
        
        self.assertEqual(len(messages), 2)
        
        self.assertEqual(messages[0].sender, "Alice2")
        self.assertEqual(messages[0].timestamp, "9:29:26 PM")
        self.assertEqual(messages[0].content, "::sigh::")
        
        self.assertEqual(messages[1].sender, "Bob2")
        self.assertEqual(messages[1].timestamp, "9:29:48 PM")
        self.assertEqual(messages[1].content, "do I?")
    
    def test_parse_span_format_mixed_patterns_in_same_conversation(self):
        """Test parsing conversation with both SPAN format variants mixed together"""
        html_content = '''<SPAN STYLE="background-color: #ffffff;"><B><FONT COLOR="#0000ff">Alice<SPAN STYLE="font-size: xx-small;"> (10:54:39 PM)</SPAN></B></FONT><FONT COLOR="#0000ff" SIZE="2">: </FONT><FONT SIZE="2">Pattern 1 message</FONT></SPAN><BR>
<SPAN STYLE="background-color: #ffffff;"><FONT COLOR="#ff0000" FACE="Times New Roman">Bob<SPAN STYLE="font-size: xx-small;"> (10:54:42 PM)</SPAN></B>:</FONT><FONT COLOR="#000000"> Pattern 2 message</FONT><BR></SPAN>
<SPAN STYLE="background-color: #ffffff;"><B><FONT COLOR="#0000ff">Alice<SPAN STYLE="font-size: xx-small;"> (10:54:45 PM)</SPAN></B></FONT><FONT COLOR="#0000ff" SIZE="2">: </FONT><FONT SIZE="2">Back to pattern 1</FONT></SPAN><BR>'''
        
        messages = self.parser.parse(html_content)
        
        self.assertEqual(len(messages), 3)
        
        self.assertEqual(messages[0].sender, "Alice")
        self.assertEqual(messages[0].timestamp, "10:54:39 PM")
        self.assertEqual(messages[0].content, "Pattern 1 message")
        
        self.assertEqual(messages[1].sender, "Bob")
        self.assertEqual(messages[1].timestamp, "10:54:42 PM")
        self.assertEqual(messages[1].content, "Pattern 2 message")
        
        self.assertEqual(messages[2].sender, "Alice")
        self.assertEqual(messages[2].timestamp, "10:54:45 PM")
        self.assertEqual(messages[2].content, "Back to pattern 1")


class TestAIMParserFactory(unittest.TestCase):
    def setUp(self):
        self.factory = AIMParserFactory()
    
    def test_factory_selects_comment_based_parser_for_comment_format(self):
        """Test that factory correctly identifies comment-based format"""
        comment_html = '''<B><FONT COLOR="#0000ff">Alice<!-- (10:57:26 PM)--></B></FONT>: <FONT>Hey there!</FONT><BR>'''
        
        parser = self.factory.get_parser(comment_html)
        
        self.assertIsInstance(parser, CommentBasedParser)
        self.assertTrue(parser.can_parse(comment_html))
    
    def test_factory_selects_span_based_parser_for_span_format(self):
        """Test that factory correctly identifies SPAN-based format"""
        span_html = '''<SPAN STYLE="background-color: #ffffff;"><B><FONT COLOR="#ff0000">Bob<SPAN STYLE="font-size: xx-small;"> (10:57:30 PM)</SPAN></B></FONT><FONT>Hi Alice!</FONT></SPAN><BR>'''
        
        parser = self.factory.get_parser(span_html)
        
        self.assertIsInstance(parser, SpanBasedParser)
        self.assertTrue(parser.can_parse(span_html))
    
    def test_factory_defaults_to_comment_parser_for_unknown_format(self):
        """Test that factory falls back to comment parser for unrecognized formats"""
        unknown_html = '''<div>Some unknown format</div>'''
        
        parser = self.factory.get_parser(unknown_html)
        
        self.assertIsInstance(parser, CommentBasedParser)
    
    def test_comment_parser_can_parse_detection(self):
        """Test CommentBasedParser.can_parse() method"""
        parser = CommentBasedParser()
        
        # Should detect comment format
        comment_html = '''<B><FONT>Alice<!-- (10:57:26 PM)--></B></FONT>: <FONT>Hey!</FONT>'''
        self.assertTrue(parser.can_parse(comment_html))
        
        # Should reject SPAN format
        span_html = '''<SPAN STYLE="background-color: #ffffff;"><B><FONT>Bob<SPAN> (10:57:30 PM)</SPAN></B></FONT></SPAN>'''
        self.assertFalse(parser.can_parse(span_html))
        
        # Should reject unknown format
        unknown_html = '''<div>Unknown format</div>'''
        self.assertFalse(parser.can_parse(unknown_html))
    
    def test_span_parser_can_parse_detection(self):
        """Test SpanBasedParser.can_parse() method"""
        parser = SpanBasedParser()
        
        # Should detect SPAN format
        span_html = '''<SPAN STYLE="background-color: #ffffff;"><B><FONT>Bob<SPAN> (10:57:30 PM)</SPAN></B></FONT></SPAN>'''
        self.assertTrue(parser.can_parse(span_html))
        
        # Should reject comment format
        comment_html = '''<B><FONT>Alice<!-- (10:57:26 PM)--></B></FONT>: <FONT>Hey!</FONT>'''
        self.assertFalse(parser.can_parse(comment_html))
        
        # Should reject unknown format
        unknown_html = '''<div>Unknown format</div>'''
        self.assertFalse(parser.can_parse(unknown_html))


if __name__ == '__main__':
    unittest.main()