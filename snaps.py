import sys
import datetime
from getpass import getpass
from collections import defaultdict
import argparse

import requests
import plotille


def terminal_size():
	import fcntl, termios, struct
	h, w, hp, wp = struct.unpack('HHHH',
		fcntl.ioctl(0, termios.TIOCGWINSZ,
		struct.pack('HHHH', 0, 0, 0, 0)))
	return w, h


class BadLoginException(Exception):
	pass


class API:
	URL_PREFIX = 'https://snaps.dropud.nu/'
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
		data = method(url, *args, **kwargs, headers={
			'Authorization': f'Token {self.token}'
		}).json()

		if isinstance(data, dict) and 'success' in data and not data['success']:
			print(data)

		return data

	def get(self, *args, **kwargs):
		return self.request(requests.get, *args, **kwargs)

	def post(self, *args, **kwargs):
		return self.request(requests.post, *args, **kwargs)

	def get_events(self):
		return self.get('events/')

	def get_event(self, event_id):
		return self.get(f'events/{event_id}/')

	def create_event(self, event_name):
		return self.post(f'events/', {
			'name': event_name,
		})

	def join_event(self, event_id):
		return self.post(f'events/{event_id}/join/')

	def create_drink_event(self, event_id):
		return self.post(f'events/{event_id}/create_drinkevent/')

	def get_users(self):
		return self.get('users/')


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


y_previous = set()
def int_formatter(val, chars, delta, left=False):
	if left:
		dt = datetime.datetime.fromtimestamp(val)
		val = dt.strftime('%H:%M')
	else:
		val = int(val)
		if val in y_previous:
			val = ''
		else:
			y_previous.add(val)

	align = '<' if left else ''
	return '{:{}{}}'.format(val, align, chars)


def plot_drink_events(event, users):
	global y_previous

	drink_events = event['drink_events']
	if not drink_events:
		print('No drink events so far...')
		return

	usernames = {}
	for user in users:
		usernames[user['id']] = user['username']

	user_drink_events = defaultdict(list)

	for drink_event in drink_events:
		drink_event['datetime'] = datetime.datetime.fromisoformat(drink_event['datetime'].rstrip('Z'))

		user_drink_events[drink_event['user']].append(drink_event)

	first_de = min(drink_events, key=lambda de: de['datetime'])
	last_de = max(drink_events, key=lambda de: de['datetime'])

	w, h = terminal_size()
	margin_w, margin_h = [20] * 2

	fig = plotille.Figure()
	fig.width = w - margin_w
	fig.height = h - margin_h
	fig.register_label_formatter(float, int_formatter)
	fig.set_x_limits(min_=first_de['datetime'].timestamp(), max_=last_de['datetime'].timestamp())
	fig.set_y_limits(min_=0, max_=max(len(evs) for evs in user_drink_events.values()))
	fig.color_mode = 'byte'

	user_des = sorted(user_drink_events.items(), key=lambda des: -len(des[1]))

	for user_id, evs in user_des:
		xs = [e['datetime'] for e in evs]
		ys = list(range(1, len(evs) + 1))
		fig.plot(xs, ys, lc=user_id, label=f'{usernames[user_id]} ({len(evs)})')

	y_previous = set()
	print(fig.show(legend=True))


if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='snaps')
	parser.add_argument('--test', action='store_true')

	args = parser.parse_args()

	while True:
		if args.test:
			username, password = ['test'] * 2
		else:
			username = input('Username: ')
			password = getpass('Password: ')

		try:
			api = API(username, password)
			break
		except BadLoginException:
			print('Wrong username/password combination. Try again.')

	events = api.get_events()

	options = [e['name'] for e in events]

	if args.test:
		event_index = 0
	else:
		event_index = choose('Choose event:', options, {
			'c': 'create',
		})

	if event_index is None:
		sys.exit()
	elif event_index == 'create':
		event_name = input('Event name: ')
		event_id = api.create_event(event_name)['id']

		print(f'Created {event_name}')

		event = api.get_event(event_id)
	else:
		event = events[event_index]
		event_id = event['id']
		api.join_event(event_id)

		print(f'Joined {event["name"]}')

	while True:
		users = api.get_users()
		plot_drink_events(event, users)

		try:
			a = input('Have drinked? ')
		except (KeyboardInterrupt, EOFError):
			sys.exit()

		if a.lower() == 'y':
			api.create_drink_event(event_id)
		else:
			print(':(')

		event = api.get_event(event_id)
