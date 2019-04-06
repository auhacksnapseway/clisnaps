import sys
from getpass import getpass
import requests


class BadLoginException(Exception):
	pass


class API:
	URL_PREFIX = 'https://snapsecounter.serveo.net/'
	LOGIN_URL = URL_PREFIX + 'api-token-auth/'
	API_PREFIX = URL_PREFIX + 'api/'

	def __init__(self, username, password):
		r = requests.post(self.LOGIN_URL, {
			'username': username,
			'password': password,
		})

		self.token = r.json().get('token')
		if not self.token:
			raise BadLoginException

	def request(self, method, path, *args, **kwargs):
		url = self.API_PREFIX + path
		return method(url, *args, **kwargs, headers={
			'Authorization': f'Token {self.token}'
		}).json()

	def get(self, *args, **kwargs):
		return self.request(requests.get, *args, **kwargs)

	def post(self, *args, **kwargs):
		return self.request(requests.post, *args, **kwargs)

	def get_events(self):
		return self.get('events/')

	def create_event(self, event_name):
		return self.post(f'events/', {
			'name': event_name,
		})

	def join_event(self, event_id):
		return self.post(f'events/{event_id}/join/')

	def create_drink_event(self, event_id):
		return self.post(f'events/{event_id}/create_drinkevent/')


def choose(title, options, kwopts={}):
	kwopts['q'] = None

	print(title)
	for i, option in enumerate(options):
		print(f'  {i + 1}) {option}')

	print()
	while True:
		try:
			opt = input(f'Choose an option (or [{"".join(kwopts.keys())}]): ')
		except (KeyboardInterrupt, EOFError):
			return None

		if opt.lower() in kwopts:
			return kwopts[opt.lower()]

		try:
			o = int(opt)
		except ValueError:
			continue

		if 1 <= o <= len(options):
			return o - 1


if __name__ == '__main__':
	while True:
		username = input('Username: ')
		password = getpass('Password: ')

		try:
			api = API(username, password)
			break
		except BadLoginException:
			print('Wrong username/password combination. Try again.')

	events = api.get_events()

	options = [e['name'] for e in events]
	event_index = choose('Choose event:', options, {
		'c': 'create',
	})

	if event_index is None:
		sys.exit()
	elif event_index == 'create':
		event_name = input('Event name: ')
		event_id = api.create_event(event_name)['id']

		print(f'Created {event_name}')
	else:
		event = events[event_index]
		event_id = event['id']
		api.join_event(event_id)

		print(f'Joined {event["name"]}')

	while True:
		try:
			a = input('Have drinked? ')
		except (KeyboardInterrupt, EOFError):
			sys.exit()

		if a.lower() == 'y':
			api.create_drink_event(event_id)
		else:
			print(':(')
