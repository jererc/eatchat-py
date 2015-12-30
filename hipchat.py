import requests

BASE_URL = 'https://api.hipchat.com'


class HipChatClient(object):

    def __init__(self, api_token, from_name=None):
        self.url_params = {'auth_token': api_token}
        self.headers = {'content-type': 'application/json'}
        self.from_name = from_name

    def _get(self, url):
        res = requests.get(url, headers=self.headers,
                params=self.url_params)
        if 200 <= res.status_code < 400:
            return res.json()
        raise Exception('error: %s' % res.text)

    def _post(self, url, data):
        res = requests.post(url, headers=self.headers,
                params=self.url_params, json=data)
        if 200 <= res.status_code < 400:
            return True
        raise Exception('error: %s' % res.text)

    def _iter_rooms(self, per_page=1000):
        url = '%s/v2/room?&max-results=%s' % (BASE_URL, per_page)
        while url:
            res = self._get(url)
            for info in res['items']:
                yield info
            url = res['links'].get('next')

    def get_room_id(self, room):
        try:
            return int(room)
        except ValueError:
            for room_info in self._iter_rooms():
                if room_info['name'] == room:
                    return room_info['id']
        raise Exception('invalid room id or name "%s"' % room)

    def send_message(self, room_id, message, message_format='html',
            color='green', notify=True):
        url = '%s/v2/room/%s/notification' % (BASE_URL, room_id)
        data = {
            'message': message,
            'message_format': message_format,
            'color': color,
            'notify': notify,
        }
        if self.from_name:
            data['from'] = self.from_name
        self._post(url, data=data)
