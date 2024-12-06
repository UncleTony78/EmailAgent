from crewai import Agent
from langchain.tools import Tool
from typing import List, Dict
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google.cloud import aiplatform
import os
import pickle
import base64
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

class GmailTools:
    def __init__(self):
        self.SCOPES = [
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.send',
            'https://www.googleapis.com/auth/gmail.modify'
        ]
        self.creds = None
        self.service = None
        self.authenticate()

    def authenticate(self):
        """Handle Gmail authentication"""
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                self.creds = pickle.load(token)
                
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_config({
                    "installed": {
                        "client_id": os.getenv('GOOGLE_CLIENT_ID'),
                        "client_secret": os.getenv('GOOGLE_CLIENT_SECRET'),
                        "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob"],
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token"
                    }
                }, self.SCOPES)
                self.creds = flow.run_local_server(port=0)
                
            with open('token.pickle', 'wb') as token:
                pickle.dump(self.creds, token)
                
        self.service = build('gmail', 'v1', credentials=self.creds)

    def read_emails(self, max_results: int = 10, query: str = None) -> List[Dict]:
        """Read emails from Gmail"""
        results = self.service.users().messages().list(
            userId='me', 
            maxResults=max_results,
            q=query
        ).execute()
        
        messages = results.get('messages', [])
        emails = []
        
        for message in messages:
            msg = self.service.users().messages().get(
                userId='me', 
                id=message['id']
            ).execute()
            
            headers = msg['payload']['headers']
            subject = next(h['value'] for h in headers if h['name'] == 'Subject')
            sender = next(h['value'] for h in headers if h['name'] == 'From')
            
            emails.append({
                'id': message['id'],
                'subject': subject,
                'sender': sender,
                'snippet': msg['snippet']
            })
            
        return emails

    def send_email(self, to: str, subject: str, body: str) -> Dict:
        """Send an email"""
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        sent_message = self.service.users().messages().send(
            userId='me',
            body={'raw': raw}
        ).execute()
        
        return {'message_id': sent_message['id']}

class EmailTools:
    def __init__(self):
        self.gmail_tools = GmailTools()
        
    def get_tools(self):
        return [
            Tool(
                name="ReadEmails",
                func=self.gmail_tools.read_emails,
                description="Read emails from Gmail. Parameters: max_results (int, optional), query (str, optional)"
            ),
            Tool(
                name="SendEmail",
                func=self.gmail_tools.send_email,
                description="Send an email. Parameters: to (str), subject (str), body (str)"
            )
        ]

def create_jared_crew():
    # Initialize tools
    email_tools = EmailTools()
    
    # Email Reader Agent
    email_reader = Agent(
        role='Email Reader',
        goal='Efficiently read and understand email content',
        backstory="""You are an expert at reading and comprehending emails. 
        Your responsibility is to process email content and extract key information.""",
        tools=email_tools.get_tools(),
        verbose=True
    )
    
    # Email Analyzer Agent
    email_analyzer = Agent(
        role='Email Analyzer',
        goal='Analyze emails and provide insights',
        backstory="""You are an expert at analyzing email content and identifying patterns, 
        priorities, and action items. You work with the Email Reader to process information.""",
        tools=email_tools.get_tools(),
        verbose=True
    )
    
    # Email Composer Agent
    email_composer = Agent(
        role='Email Composer',
        goal='Compose and send effective emails',
        backstory="""You are an expert at writing clear and effective emails. 
        You can draft responses and new emails based on analysis and requirements.""",
        tools=email_tools.get_tools(),
        verbose=True
    )
    
    return {
        'reader': email_reader,
        'analyzer': email_analyzer,
        'composer': email_composer
    }
