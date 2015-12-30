#!/usr/bin/env python
import argparse
import time
from datetime import datetime
import imaplib
import email
import re

from hipchat import HipChatClient

from lxml import html

RE_DATE = re.compile(r'(.*)\s+\+\d{4}$')
FROM_NAME = 'PopChef'
ORDER_URL = 'https://eatpopchef.com/'


class ImapClient(object):

    def __init__(self, host, port, username, password):
        self.client = imaplib.IMAP4_SSL(host, port)
        self.client.login(username, password)
        self.client.select()

    def close(self):
        try:
            self.client.close()
        except Exception:
            pass
        self.client.logout()

    def _get_date(self, message):
        try:
            date_str = RE_DATE.search(message['date']).group(1)
        except Exception, e:
            raise Exception('failed to parse date "%s": %s' % (message['date'], str(e)))
        return datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S')

    def _extract_body(self, payload):
        if not isinstance(payload, basestring):
            return '\n'.join([self._extract_body(p.get_payload(decode=True))
                    for p in payload])
        return payload

    def get_message(self, from_email, subject, date_min):
        query = '(SENTSINCE %s HEADER Subject "%s")' % (date_min.strftime('%d-%b-%Y'), subject)
        result, data = self.client.uid('search', None, query)
        for uid in data[0].split():
            result_, data_ = self.client.uid('fetch', uid, '(RFC822)')
            msg = email.message_from_string(data_[0][1])
            from_email_ = email.utils.parseaddr(msg['from'])[-1]
            if from_email_ != from_email:
                continue
            return self._extract_body(msg.get_payload())


def parse_cmdline():
    parser = argparse.ArgumentParser(description='Popchef to hipchat')
    parser.add_argument('--hipchat_token', type=str, required=True,
            help='hipchat API token')
    parser.add_argument('--hipchat_room', type=str, required=True,
            help='hipchat room name')
    parser.add_argument('--imap_host', type=str, required=True,
            help='IMAP host')
    parser.add_argument('--imap_port', type=int, default=993,
            help='IMAP port')
    parser.add_argument('--imap_username', type=str, required=True,
            help='IMAP username')
    parser.add_argument('--imap_password', type=str, required=True,
            help='IMAP password')
    parser.add_argument('--from_email', type=str, default='hello@eatpopchef.com',
            help='from email')
    parser.add_argument('--subject', type=str, default='ardoise',
            help='subject term')
    parser.add_argument('--timeout', type=int, default=30,
            help='timeout in minutes')
    return parser.parse_args()

def get_email_message(host, port, username, password,
        from_email, subject, timeout):

    def sleep(delay, message):
        print message
        time.sleep(delay)

    now = datetime.utcnow()
    date_min = datetime(now.year, now.month, now.day)
    client = None
    start_time = time.time()
    while time.time() - start_time < timeout * 60:
        try:
            client = ImapClient(host=host, port=port,
                    username=username, password=password)
            res = client.get_message(from_email=from_email,
                    subject=subject, date_min=date_min)
            if res:
                return res
        except Exception, e:
            sleep(5, 'failed to get email message: %s, retrying in a few seconds' % str(e))
            continue
        finally:
            if client:
                client.close()
                client = None
        sleep(30, 'no recent message from %s, retrying in a few seconds...' % from_email)

    raise Exception('no new message from %s' % from_email)

def get_hipchat_messages(message):

    def get_message(element):
        img_url = element.cssselect('img')[0].get('src')
        res = element.cssselect('td.mcnTextContent div strong')
        if res:
            desc = res[0].text.encode('utf-8')
            return {'message': '<img width=240 src="%s"><br><strong>%s</strong>' % (img_url, desc)}

    elements = html.fromstring(message).cssselect('td.mcnImageCardBlockInner')
    return [m for m in map(get_message, elements) if m]

def main():
    args = parse_cmdline()
    email_message = get_email_message(args.imap_host, args.imap_port,
            args.imap_username, args.imap_password, args.from_email,
            args.subject, args.timeout)
    hc = HipChatClient(api_token=args.hipchat_token, from_name=FROM_NAME)
    hc.send_message(args.hipchat_room, message=FROM_NAME, color='gray')
    for message in get_hipchat_messages(email_message):
        hc.send_message(args.hipchat_room, **message)
    hc.send_message(args.hipchat_room,
            message='<a href="%s">Order %s</a>' % (ORDER_URL, FROM_NAME), color='gray')


if __name__ == '__main__':
    main()
