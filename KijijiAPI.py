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
import configparser
import http.cookiejar
import os
import random
import sys
import urllib.request
import urllib.parse

if sys.version_info < (3, 0):
	raise Exception('This script is made for Python 3.0 or higher')

def randomize_spaces(input):
	words = input.split(' ')
	output = ''
	for w in words:
		output += ' '*(1+random.randrange(3))+w
	return output

class KijijiAPIException(Exception):
	def __init__(self, dump):
		with open('/tmp/kijiji-api-dump', 'w') as dumpfile:
			dumpfile.write(dump)

	def __str__(self):
		return 'Last downloaded page saved in "/tmp/kijiji-api-dump".'

class SignInException(KijijiAPIException):
	def __str__(self):
		return 'Could not sign in.\n'+super().__str__()

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

	def post_image(self, imagefile):
		name = os.path.basename(imagefile)

		url = 'http://api-p.classistatic.com/api/image/upload'
		self.images.append(imagefile)

	def post_ad(self, postvarsfile):
		url = 'http://montreal.kijiji.ca/c-PostAd'

		postdata = {}

		postvars = open(postvarsfile, 'rt')
		for line in postvars:
			line = line.strip()
			key = line[:line.index('=')]
			val = line[line.index('=')+1:]

			if key == 'Photo':
				# TODO
				print('TODO: post photo!')
			elif key == 'Description':
				val = randomize_spaces(val)

			postdata[key] = val
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
	parser.add_argument('p', metavar='post-vars.txt',
						help='file containing the POST vars')
	parser.add_argument('-i', metavar='img1.jpg,img2.png',
						help='images to join with the ad')
	args = parser.parse_args()

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
