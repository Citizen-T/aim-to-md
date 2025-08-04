import unittest
from datetime import datetime
from src.aim_parser import AIMParser, Message


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


if __name__ == '__main__':
    unittest.main()