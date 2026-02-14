import os
import sys
import argparse
import base64
import json
from email.message import EmailMessage
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Force UTF-8 encoding for stdout
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Required scopes for reading, modifying (labels), and creating drafts
SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive.metadata.readonly'
]

def get_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Error refreshing credentials: {e}")
                creds = None
        
        if not creds:
            if not os.path.exists('credentials.json'):
                print("Error: credentials.json not found.")
                return None
            try:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            except Exception as e:
                print(f"Error during OAuth flow: {e}")
                return None
            
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
            
    return build('gmail', 'v1', credentials=creds)

def count_unread():
    service = get_service()
    if not service:
        print("Service not available.")
        return 0
    try:
        results = service.users().messages().list(userId='me', q='is:unread').execute()
        messages = results.get('messages', [])
        return len(messages)
    except Exception as e:
        print(f"Error counting unread messages: {e}")
        return 0

def list_unread(limit=10):
    service = get_service()
    if not service: 
        print("Service not available.")
        return []
    try:
        results = service.users().messages().list(userId='me', q='is:unread', maxResults=limit).execute()
        messages = results.get('messages', [])
        
        if not messages:
            print("No unread messages found.")
            return []
        
        detailed_messages = []
        for msg in messages:
            m = service.users().messages().get(userId='me', id=msg['id']).execute()
            if not m:
                print(f"Could not retrieve details for message ID: {msg['id']}")
                continue
            payload = m.get('payload', {})
            headers = payload.get('headers', [])
            
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            from_addr = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
            
            body = ""
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain' and 'body' in part and 'data' in part['body']:
                        try:
                            body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                        except: pass
                        break
            elif 'body' in payload and 'data' in payload['body']:
                try:
                    body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
                except: pass

            detailed_messages.append({
                'id': msg['id'],
                'from': from_addr,
                'subject': subject,
                'snippet': m.get('snippet', ''),
                'body': body
            })
        return detailed_messages
    except Exception as e:
        print(f"Error listing unread messages: {e}")
        return []

def mark_as_read(msg_id):
    service = get_service()
    if not service: return False
    try:
        service.users().messages().batchModify(
            userId='me',
            body={'ids': [msg_id], 'removeLabelIds': ['UNREAD']}
        ).execute()
        return True
    except Exception as e:
        print(f"Error marking message {msg_id} as read: {e}")
        return False

def create_draft(to, subject, body):
    service = get_service()
    if not service: return
    try:
        message = EmailMessage()
        message.set_content(body)
        message['To'] = to
        message['From'] = 'me'
        message['Subject'] = subject
        
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {
            'message': {
                'raw': encoded_message
            }
        }
        service.users().drafts().create(userId="me", body=create_message).execute()
        print(f"Draft created for {to}")
    except Exception as e:
        print(f"Error creating draft: {e}")

def main():
    parser = argparse.ArgumentParser(description='Gmail API Tool')
    subparsers = parser.add_subparsers(dest='command')
    
    list_p = subparsers.add_parser('list-unread', help='List unread emails')
    list_p.add_argument('--limit', type=int, default=10)
    list_p.add_argument('--json', action='store_true', help='Output as JSON')

    count_p = subparsers.add_parser('count-unread', help='Count unread emails')
    
    mark_p = subparsers.add_parser('mark-read', help='Mark email as read')
    mark_p.add_argument('id')
    
    draft_p = subparsers.add_parser('draft', help='Create a draft')
    draft_p.add_argument('--to', required=True)
    draft_p.add_argument('--subject', required=True)
    draft_p.add_argument('--body', required=True)
    
    args = parser.parse_args()
    
    if args.command == 'list-unread':
        msgs = list_unread(args.limit)
        if args.json:
            print(json.dumps(msgs, ensure_ascii=False))
        else:
            for m in msgs:
                print(f"ID: {m['id']} | FROM: {m['from']} | SUBJECT: {m['subject']}")
                print(f"BODY: {m['body'][:200]}...")
                print("---")
    elif args.command == 'count-unread':
        count = count_unread()
        print(f"You have {count} unread emails.")
    elif args.command == 'mark-read':
        if mark_as_read(args.id):
            print(f"Marked {args.id} as read.")
    elif args.command == 'draft':
        create_draft(args.to, args.subject, args.body)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()