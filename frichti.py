#!/usr/bin/env python
import argparse

from hipchat import HipChatClient

from lxml import html
import requests

FROM_NAME = 'Frichti'
BATCH_SIZE = 3


def parse_cmdline():
    parser = argparse.ArgumentParser(description='Popchef to hipchat')
    parser.add_argument('--url', type=str, default='http://frichti.co',
            help='frichti URL')
    parser.add_argument('--hipchat_token', type=str, required=True,
            help='hipchat API token')
    parser.add_argument('--hipchat_room', type=str, required=True,
            help='hipchat room id or name')
    return parser.parse_args()

def get_body(url):
    res = requests.get(url)
    if 200 <= res.status_code < 300:
        return res.text
    raise Exception('error: %s' % res.text)

def iter_hipchat_messages(data):

    def get_img_url(element):
        res = element.cssselect('div.product-grid-image--centered')
        if res:
            desc = res[0].get('data-src')
            if desc:
                return 'http://%s' % desc.lstrip('/')

    def get_description(element):
        res = el.cssselect('div.product-grid-content span')
        if res:
            return res[0].text.encode('utf-8')

    def get_message(batch, color):
        return {
            'message': '<table><tr>%s</tr></table>' % ''.join(batch),
            'color': color,
            }

    tree = html.fromstring(data)
    batch = []
    for name, id_, color in [
            ('Entrees', 'entree', 'yellow'),
            ('Plats', 'plat', 'green'),
            ]:
        yield {'message': '%s:' % name, 'color': color}

        for el in tree.cssselect('#%s div.grid-item' % id_):
            img_url = get_img_url(el)
            if not img_url:
                continue
            desc = get_description(el)
            if not desc:
                continue
            cell = '<td><img width=160 src="%s"><br><strong>%s</strong></td>' % (img_url, desc)
            batch.append(cell)
            if len(batch) == BATCH_SIZE:
                yield get_message(batch, color=color)
                batch = []

        if batch:
            yield get_message(batch, color=color)
            batch = []

def main():
    args = parse_cmdline()
    data = get_body(args.url)
    hc = HipChatClient(api_token=args.hipchat_token, from_name=FROM_NAME)
    room_id = hc.get_room_id(args.hipchat_room)
    hc.send_message(room_id, message=FROM_NAME, color='gray')
    for message in iter_hipchat_messages(data):
        hc.send_message(room_id, **message)
    hc.send_message(room_id,
            message='<a href="%s">Order %s</a>' % (args.url, FROM_NAME), color='gray')


if __name__ == '__main__':
    main()
