#!/usr/bin/python
# -*- coding: utf-8 -*-

import tornado
import json
from bson.json_util import dumps

import glob
import glob2
import shutil
import time
#from tornado import web
from tornado import ioloop
from tornado import auth
from tornado import escape
from tornado import httpserver
from tornado import options
from tornado import web
#from tornado.web import asynchronous
from tornado import gen
#import git
from git import Repo, Actor
import os
from PIL import Image
import qrcode

import re
from six.moves.html_parser import HTMLParser
from w3lib.html import replace_entities
from . import _sql, BaseHandler, sendMail
import subprocess

class module(BaseHandler):
    #@asynchronous
    def get(self, module=None):
        self.set_header('Content-Type', 'application/json')

        #module = get_argument('name')
        module_data = self.db_web.Modules.find({'_id': module})
        module_data = list(module_data)
        output = json.dumps(module_data)
        self.write(output)
        self.finish()


class modules(BaseHandler):
    #@asynchronous
    def get(self, module = None):
        self.set_header('Content-Type', 'application/json')

        module_data = self.db_web.Modules.find()
        module_data = list(module_data)
        output = json.dumps(module_data)
        self.write(output)
        self.finish()
