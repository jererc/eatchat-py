import requests


class HipChatClient(object):

    def __init__(self, api_token, from_name=None):
        self.url_params = {'auth_token': api_token}
        self.headers = {'content-type': 'application/json'}
        self.from_name = from_name

    def _post(self, url, data):
        res = requests.post(url, headers=self.headers,
                params=self.url_params, json=data)
        if 200 <= res.status_code < 400:
            return True
        raise Exception('error: %s' % res.text)

    def send_message(self, room, message, message_format='html',
            color='green', notify=True):
        url = 'https://api.hipchat.com/v2/room/%s/notification' % room
        data = {
            'message': message,
            'message_format': message_format,
            'color': color,
            'notify': notify,
        }
        if self.from_name:
            data['from'] = self.from_name
        self._post(url, data=data)
