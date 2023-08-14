"""
Python 2.7/3.6 compatible
GMAIL Accounts
A script to download email attachments from specific email addresses
Please edit the following details to work:
YOUR_EMAIL_ADDRESS
YOUR_EMAIL_PASSWORD
LABEL - Inbox, Trash, Archive, ...
RECEIVING_EMAIL_ADDRESS
RECEIVING_SUBJECT - '*' for all OR 'Title of Subject'
On imap search params:
Remove the parameters you don't require for a general search
"""
import email
import getpass
import imaplib
import os
import sys

detach_dir = '.'
if 'attachments' not in os.listdir(detach_dir):
    os.mkdir('attachments')
try:
    imapSession = imaplib.IMAP4_SSL('imap.gmail.com')
    typ, accountDetails = imapSession.login('YOUR_EMAIL_ADDRESS', 'YOUR_EMAIL_PASSWORD')
    imapSession.select('LABEL')
    typ, data = imapSession.search(None,'(SINCE "1-Jan-2012" BEFORE "02-Jan-2012" FROM "RECEIVING_EMAIL_ADDRESS" SUBJECT "RECEIVING_SUBJECT")')
    print(typ, data)
    print('Search...')
    for msgId in data[0].split():
        typ, messageParts = imapSession.fetch(msgId, '(RFC822)')
        emailBody = messageParts[0][1]
        raw_email_string = emailBody.decode('utf-8')
        mail = email.message_from_string(raw_email_string)#
        print('emailbody complete ...')
        for part in mail.walk():
            if part.get_content_maintype() == 'multipart':
                print(part.as_string())
                continue
            if part.get('Content-Disposition') is None:
                print(part.as_string())
                continue
            fileName = part.get_filename()
            print('file names processed ...')
            if bool(fileName):
                filePath = os.path.join(detach_dir, 'attachments', fileName)
                if not os.path.isfile(filePath):
                    print(fileName)
                    fp = open(filePath, 'wb')
                    fp.write(part.get_payload(decode=True))
                    fp.close()
                    print('fp closed ...')
    imapSession.close()
    imapSession.logout()
except:
    print('Not able to download all attachments.')