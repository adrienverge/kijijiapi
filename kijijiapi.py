#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2013 Adrien Vergé

"""Kijiji API

Robot to post ads on Kijiji.

This set of bash functions allow you to automatically post ads on the Kijiji
advertisement community. Using a crontab, you can program it to post your ad
regularly and make sure more users will see it.

"""

__author__ = "Adrien Vergé"
__copyright__ = "Copyright 2013, Adrien Vergé"
__license__ = "GPL"
__version__ = "2.0"

import argparse
import codecs
import configparser
import http.cookiejar
import io
import os
import random
import mimetypes
import sys
import urllib.request
import urllib.parse
import uuid

if sys.version_info < (3, 0):
	raise Exception('This script is made for Python 3.0 or higher')

def randomize_spaces(input):
	words = input.split(' ')
	output = ''
	for w in words:
		output += ' '*(1+random.randrange(3))+w
	return output

class MultipartFormdataEncoder(object):
	"""Class to HTTP POST multipart/form-data encoded data

	Taken from http://stackoverflow.com/questions/1270518

	"""
	def __init__(self):
		self.boundary = uuid.uuid4().hex
		self.content_type = 'multipart/form-data; boundary={}'.format(self.boundary)

	@classmethod
	def u(cls, s):
		if isinstance(s, bytes):
			s = s.decode('utf-8')
		return s

	def iter(self, fields, files):
		"""
		fields is a sequence of (name, value) elements for regular form fields.
		files is a sequence of (name, filename, file-type) elements for data to be uploaded as files
		Yield body's chunk as bytes
		"""
		encoder = codecs.getencoder('utf-8')
		for (key, value) in fields:
			key = self.u(key)
			yield encoder('--{}\r\n'.format(self.boundary))
			yield encoder(self.u('Content-Disposition: form-data; name="{}"\r\n').format(key))
			yield encoder('\r\n')
			if isinstance(value, int) or isinstance(value, float):
				value = str(value)
			yield encoder(self.u(value))
			yield encoder('\r\n')
		for (key, filename, fd) in files:
			key = self.u(key)
			filename = self.u(filename)
			yield encoder('--{}\r\n'.format(self.boundary))
			yield encoder(self.u('Content-Disposition: form-data; name="{}"; filename="{}"\r\n').format(key, filename))
			yield encoder('Content-Type: {}\r\n'.format(mimetypes.guess_type(filename)[0] or 'application/octet-stream'))
			yield encoder('\r\n')
			with fd:
				buff = fd.read()
				yield (buff, len(buff))
			yield encoder('\r\n')
		yield encoder('--{}--\r\b'.format(self.boundary))

	def encode(self, fields, files):
		body = io.BytesIO()
		for chunk, chunk_len in self.iter(fields, files):
			body.write(chunk)
		return self.content_type, body.getvalue()

class KijijiAPIException(Exception):
	def __init__(self, dump=None):
		if dump:
			with open('/tmp/kijiji-api-dump', 'w') as dumpfile:
				dumpfile.write(dump)

	def __str__(self):
		return 'Last downloaded page saved in "/tmp/kijiji-api-dump".'

class SignInException(KijijiAPIException):
	def __str__(self):
		return 'Could not sign in.\n'+super().__str__()

class ListAdsException(KijijiAPIException):
	def __str__(self):
		return 'Could not list ads.\n'+super().__str__()

class PostImageException(KijijiAPIException):
	def __str__(self):
		return 'Could not post image.\n'+super().__str__()

class PostAdException(KijijiAPIException):
	def __str__(self):
		return 'Could not post ad.\n'+super().__str__()

class KijijiAPI:
	"""This is the main class.

	"""

	def __init__(self):
		config_file = os.path.dirname(__file__)+'/config.ini'
		self.read_config(config_file)

		cj = http.cookiejar.CookieJar()
		opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
		opener.addheaders = [('User-agent', 'Mozilla/5.0')]
		urllib.request.install_opener(opener)

		self.images = []

	def read_config(self, path):
		self.config = configparser.ConfigParser()
		self.config.read(path)
		if (not 'account' in self.config) \
		   or self.config['account']['username'] == '' \
		   or self.config['account']['password'] == '':
			raise Exception('No username or password in config file')

	def sign_in(self):
		url = 'https://secure.kijiji.ca/montreal/s-SignIn'
		params = urllib.parse.urlencode(
			{'rup': '', 'ruq': '', 'AdId': 0, 'Mode': 'Normal',
			 'GreetingName': self.config['account']['username'],
			 'Password': self.config['account']['password'],
			 'Submit': 'Ouvrir une session'})
		params = params.encode('utf-8')

		# First time for the cookies
		f = urllib.request.urlopen(url)

		f = urllib.request.urlopen(url, params)
		page = f.read().decode('utf-8')

		if not 'Fermer la session' in page:
			raise SignInException(page)

	def list_ads(self):
		url = 'http://montreal.kijiji.ca/c-ManageMyAds'

		f = urllib.request.urlopen(url)
		page = f.read().decode('utf-8')

		try:
			start = page.index('<table id="tableDefault"')
			end = page.index('</table>', start)
			table = page[start:end]
		except ValueError:
			raise ListAdsException(page)

		ads = []
		adend = 0

		while True:
			try:
				adstart = table.index('<tr id="', adend)
				adend = table.index('</tr>', adstart)
			except ValueError:
				break

			tr = table[adstart:adend]

			id = int(tr[8:tr.index('"', 8)])

			aindex = tr.index('<a', tr.index('<td class="row" width="25%"'))
			namestart = tr.index('>', aindex) + 1
			nameend = tr.index('<', namestart)
			name = tr[namestart:nameend]

			ad = { 'id': id, 'name': name }
			ads.append(ad)

		return ads

	def post_image(self, imagefile):
		name = os.path.basename(imagefile)

		url = 'http://api-p.classistatic.com/api/image/upload'

		fields = [('Filename', name), ('r', '0'),
			('a', '1:913a6c0fec4f7a4f46321180f39d9e57ac9c8ff033971da0b9cfcccc45bef4e2'),
			('v', 'k'), ('s', '1C5000'), ('n', 'k'), ('b', '18'),
			('Upload', 'Submit Query')]
		files = [('u', name, open(imagefile, 'rb'))]
		content_type, body = MultipartFormdataEncoder().encode(fields, files)

		headers = {'User-Agent': 'Shockwave Flash',
			   'Connection': 'Keep-Alive',
			   'Cache-Control': 'no-cache',
			   'Accept': 'text/*',
			   'Content-type': content_type}

		o = urllib.parse.urlparse(url)

		tryagain = 3
		while tryagain > 0:
			try:
				conn = http.client.HTTPConnection(o.netloc)
				conn.request('POST', o.path, body, headers)
				response = conn.getresponse()
				tryagain = -1
			except ConnectionResetError:
				print('Connection reset, trying again...')
				tryagain -= 1
		if tryagain == 0:
			raise PostImageException()

		page = response.read().decode('utf-8')
		conn.close()

		if response.status != 200 or not page:
			raise PostImageException(str(response.status)+' '+response.reason)

		self.images.append(page)

	def post_ad(self, postvarsfile):
		url = 'http://montreal.kijiji.ca/c-PostAd'

		postdata = {}

		postvars = open(postvarsfile, 'rt')
		for line in postvars:
			line = line.strip()
			key = line[:line.index('=')]
			val = line[line.index('=')+1:]
			if key == 'Description':
				val = randomize_spaces(val)
			postdata[key] = val
		if self.images:
			postdata['Photo'] = ','.join(self.images)
		postvars.close()

		params = urllib.parse.urlencode(postdata)
		params = params.encode('utf-8')

		f = urllib.request.urlopen(url, params)
		page = f.read().decode('utf-8')

		if not 'votre annonce est maintenant en ligne' in page:
			raise PostAdException(page)

def main():
	"""This is the entry point of the script."""

	parser = argparse.ArgumentParser(
		description='Robot to post ads on Kijiji.')
	subparsers = parser.add_subparsers(title='subcommands',
									   help='additional help')

	parser_list = subparsers.add_parser('list', help='list ads currently displayed')
	parser_list.set_defaults(func=main_list)

	parser_post = subparsers.add_parser('post', help='post a new ad')
	parser_post.set_defaults(func=main_post)
	parser_post.add_argument('p', metavar='post-vars.txt',
							 help='file containing the POST vars')
	parser_post.add_argument('-i', metavar='img1.jpg,img2.png',
							 help='images to join with the ad')

	args = parser.parse_args()
	try:
		args.func(args)
	except AttributeError:
		parser.print_help()

def main_list(args):
	kijapi = KijijiAPI()

	print('[ ] Signing in...')
	kijapi.sign_in()

	print('[ ] Listing ads...')
	ads = kijapi.list_ads()

	if not ads:
		print('   No ad.')
	else:
		for ad in ads:
			print('%d\t%s' % (ad['id'], ad['name']))

def main_post(args):
	kijapi = KijijiAPI()

	print('[ ] Signing in...')
	kijapi.sign_in()

	if args.i:
		images = args.i.split(',')
		for img in images:
			print('[ ] Posting image "'+img+'"...')
			kijapi.post_image(img)

	print('[ ] Posting ad...')
	kijapi.post_ad(args.p)

	print('    Done!')
	sys.exit(0)

if __name__ == "__main__":
	main()
