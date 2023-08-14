import os
import base64
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
import pickle

# Define the API scope and credentials
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.modify']
CREDENTIALS_FILE = 'google_api/credentials.json'  # Your downloaded credentials JSON file

def authenticate():
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
    creds = flow.run_local_server(port=0)
    with open('google_api/token.pickle', 'wb') as token:
        pickle.dump(creds, token)

def main():
    if not os.path.exists('google_api/token.pickle'):
        authenticate()

    with open('google_api/token.pickle', 'rb') as token:
        creds = pickle.load(token)

    service = build('gmail', 'v1', credentials=creds)

    # List messages with attachments
    results = service.users().messages().list(userId='me', q='has:attachment').execute()
    messages = results.get('messages', [])

    if not messages:
        print('No messages with attachments found.')
    else:
        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            for part in msg['payload']['parts']:
                if part['filename']:
                    att_id = part['body']['attachmentId']
                    att = service.users().messages().attachments().get(userId='me', messageId=message['id'], id=att_id).execute()
                    data = att['data']
                    file_data = base64.urlsafe_b64decode(data.encode('UTF-8'))
                    file_path = os.path.join('attachments', part['filename'])
                    with open(file_path, 'wb') as f:
                        f.write(file_data)
                    print(f"Downloaded {part['filename']}")

if __name__ == '__main__':
    if not os.path.exists('attachments'):
        os.mkdir('attachments')
    main()
