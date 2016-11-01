#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2013 Adrien Vergé

"""Kijiji API

Robot to post ads on Kijiji.

This set of bash functions allow you to automatically post ads on the Kijiji
advertisement community. Using a crontab, you can program it to post your ad
regularly and make sure more users will see it.

"""

__author__ = "Adrien Vergé"
__author_update__ = "Ravi Bhanabhai"
__copyright__ = "Copyright 2013, Adrien Vergé"
__license__ = "GPL"
__version__ = "2.1"
__date__ ="Q4 2016"

import argparse
import codecs
import configparser
import http.cookiejar
import sqlite3
import io
import os
import random
import mimetypes
import sys
import requests
import urllib.request
import urllib.parse
import json
import ssl



import uuid

if sys.version_info < (3, 0):
	raise Exception('This script is made for Python 3.0 or higher')

def randomize_spaces(input):
	words = input.split('+')
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

class DeleteAdException(KijijiAPIException):
	def __str__(self):
		return 'Could not delete ad.\n'+super().__str__()

class csrfTokenException(KijijiAPIException):
	def __str__(self):
		return 'Could not get csrf token.\n'+super().__str__()


class KijijiAPI:
	"""This is the main class."""

	def __init__(self):

		# Read config
		config_file = os.path.dirname(__file__)+'/config.ini'
		self.read_config(config_file)

		# Handle cookies
		cookiefile = self.config['account']['cookies']
		self.cj = http.cookiejar.MozillaCookieJar(cookiefile)
		try:
			self.cj.load()
		except FileNotFoundError:
			self.load_browser_cookies()
			self.save_cookies()
			print("loaded Browser Cookies")

		# Install HTTP context
		opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler(), urllib.request.HTTPCookieProcessor(self.cj))
		opener.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686) Gecko/20071127 Firefox/2.0.0.11'),
							('Connection', 'keep-alive')]
		urllib.request.install_opener(opener)

		# Init image list
		self.images = []

	def read_config(self, path):
		self.config = configparser.ConfigParser()
		self.config.read(path)
		if (not 'account' in self.config) \
		   or self.config['account']['cookies'] == '':
			raise Exception('No cookies in config file')

	def load_browser_cookies(self):

			browser_type = self.config['account']['browser']
			cookie_location = self.config['account']['browser_cookies']
			
			#Retrieve Firefox Cookies
			con = sqlite3.connect(cookie_location)
			cur = con.cursor()
			cur.execute("SELECT host, path, isSecure, expiry, name, value FROM moz_cookies WHERE baseDomain = 'kijiji.ca' ")

			for item in cur.fetchall():
				c = http.cookiejar.Cookie(0, item[4], item[5],
					None, False,
					item[0], item[0].startswith('.'), item[0].startswith('.'),
					item[1], False,
					item[2],
					item[3], item[3]=="",
					None, None, {})
				self.cj.set_cookie(c)

	def save_cookies(self):
		self.cj.save()

	def is_signed_in(self, page=None):
		if page == None:
			url = 'https://www.kijiji.ca/'
			f = urllib.request.urlopen(url)
			page = f.read().decode('utf-8')

		if page.find('<a href="/m-my-ads.html"') >= 0:
			return True

		return False

	def sign_in(self):

		#----------------
		# depreciated 
		#----------------

		url = 'https://www.kijiji.ca/'
		f = urllib.request.urlopen(url)
#		print( f.info().headers )
		page = f.read().decode('utf-8')

		if not self.is_signed_in(page):
			raise SignInException(page)

	def list_ads(self):
		
		url = 'https://www.kijiji.ca/m-my-ads.html'
		f = urllib.request.urlopen(url)
		page = f.read().decode('utf-8')
		try:
			id_start = page.index(', userId:') + 11
			id_end = id_start + 19
			userID = page[id_start:id_end]
		except ValueError:
			raise ListAdsException(page)

		url = 'https://www.kijiji.ca/j-get-my-ads.json?show=ACTIVE&user='+userID
		f = urllib.request.urlopen(url)
		page = f.read().decode('utf-8')   
		data = json.loads(page)

		ads = []

		for fullad in data['myAdEntries']:
			try:
				ad = {
				 'id': fullad['id'],
				 'title': fullad['title'],
				 'price': fullad['price'],
				 'page': fullad['pageNumber'],
				 'counter': fullad['viewCounter']
				 }
			except ValueError:
				break

			ads.append(ad)

		return ads

	def post_image(self, imagefile):
		name = os.path.basename(imagefile)

		url = 'https://www.kijiji.ca/p-upload-image.html'

		#token = self.get_eps_token()
		fields = [('s', '1C5000'), ('v', '2'), ('b', '18'),
				  ('n', 'k')] #, ('a', token)]

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

		if response.status == 303:
			# Location contains someting like:
			# http://api-p.classistatic.com/ws2/syi/EpsPostProcess.jsp?picurl=http://
			url = response.getheader('Location')
			f = urllib.request.urlopen(url)
			page = url.split('picurl=')[1] #.split('?')[0]
		elif response.status != 200 or not page:
			raise PostImageException(str(response.status)+' '+response.reason+
									 '\n\n'+page)

		self.images.append(page)

	def post_ad(self, postvarsfile):
		url = 'https://www.kijiji.ca/p-submit-ad.html'

		postdata = {}

		postvars = open(postvarsfile, 'rt')
		for line in postvars:
			line = line.strip()
			if '=' not in line:
				continue
			key = line[:line.index('=')]
			val = line[line.index('=')+1:]
			if key == 'postAdForm.description' or key == 'postAdForm.title':
				val = randomize_spaces(val)
			postdata[key] = val
		if self.images:
			for img in self.images:
				postdata['images'] = ','.join(img)
		postvars.close()

		postdata['ca.kijiji.xsrf.token'] = self.get_csrf_token('https://www.kijiji.ca/m-my-ads.html')

		params = urllib.parse.urlencode(postdata)
		params = params.encode('utf-8')

		f = urllib.request.urlopen(url, params)
		page = f.read().decode('utf-8')

		if not "My Ad's status" in page:
			raise PostAdException(page)

	def get_eps_token(self):
		url = 'https://secure.kijiji.ca/toronto/s-GetEpsToken'
		f = urllib.request.urlopen(url)
		page = f.read().decode('utf-8')

		# Looks like '1:913a6c0fec4f7a4f46321180f39d9e57d01c370eb30721cfd2c249997756ab4d'
		token = page.split("'")[1]
		return token

	def get_csrf_token(self, site):
		url = site
		f = urllib.request.urlopen(url)
		page = f.read().decode('utf-8')

		startWord = 'name="ca.kijiji.xsrf.token" value="'
		token=""
		try:
			index = page.index(startWord) + len(startWord)
			while(1):
				if( page[index] == '"' or index == 100 ):
					break
				token += page[index]
				index += 1

		except ValueError:
			raise csrfTokenException(page)

		return token

	def delete_ad(self, id):

		url = 'https://www.kijiji.ca/j-delete-ad.json'

		postdata = {}
		postdata['Action'] = 'DELETE_ADS'
		postdata['Mode'] = 'ACTIVE'
		postdata['needsRedirect'] = 'false'
		postdata['ads'] = '[{"adId":"'+id+'","reason":"PREFER_NOT_TO_SAY","otherReason":""}]'
		postdata['ca.kijiji.xsrf.token'] = self.get_csrf_token('https://www.kijiji.ca/m-my-ads.html')

		params = urllib.parse.urlencode(postdata)
		params = params.encode('utf-8')

		f = urllib.request.urlopen(url, params)
		page = f.read().decode('utf-8')

		if not 'has been successfully deleted.' in page:
			raise DeleteAdException(page)

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

	parser_post = subparsers.add_parser('delete', help='remove an existing ad')
	parser_post.set_defaults(func=main_delete)
	parser_post.add_argument('id', metavar='ID',
							 help='ad identifier (e.g. 470957281)')

	args = parser.parse_args()
	try:
		args.func(args)
	except AttributeError:
		parser.print_help()

def main_signin(kijapi):
	print('[ ] Connecting to Kijiji...')
	if kijapi.is_signed_in():
		print('[ ] Already signed in.')
	else:
		print('[ ] Signing in... ', end='')
		kijapi.sign_in()
		print('done.')

def main_savecookies(kijapi):
	print('[ ] Saving new cookies...')
	kijapi.save_cookies()

def main_list(args):
	kijapi = KijijiAPI()

	main_signin(kijapi)

	print('[ ] Listing ads... ', end='')
	ads = kijapi.list_ads()

	if not ads:
		print('no ad.')
	else:
		print('')
		for ad in ads:
			print('\t*%s\t%s\t$%s\tviews:%s\tpage:%s' % (ad['id'], ad['title'], ad['price'], ad['counter'], ad['page']))

	main_savecookies(kijapi)

def main_post(args):
	kijapi = KijijiAPI()

	main_signin(kijapi)

	if args.i:
		images = args.i.split(',')
		for img in images:
			print('[ ] Posting image "'+img+'"...')
			kijapi.post_image(img)

	print('[ ] Posting ad... ', end='')
	kijapi.post_ad(args.p)
	print('done!')

	main_savecookies(kijapi)

def main_delete(args):
	kijapi = KijijiAPI()

	main_signin(kijapi)

	print('[ ] Removing ad %s... ' % args.id, end='')
	kijapi.delete_ad(args.id)
	print('done.')

	main_savecookies(kijapi)

if __name__ == "__main__":
	main()
