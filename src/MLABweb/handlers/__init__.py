#!/usr/bin/env python
# -*- coding: utf-8 -*-

#import MySQLdb as mdb
import pymongo

import os
#import pymysql.cursors

import tornado
from requests_oauthlib import OAuth2Session

# import smtplib
# from email.mime.multipart import MIMEMultipart
# from email.mime.multipart import MIMEBase
# from email.mime.multipart import MIMEMultipart
# from email.MIMEMultipart import MIMEMultipart
# from email.MIMEBase import MIMEBase
# from email.MIMEText import MIMEText
# from email.Utils import COMMASPACE, formatdate
# from email import Encoders
import os


class BaseHandler(tornado.web.RequestHandler):

    def prepare(self):
        self.xsrf_token
        self.db_web = pymongo.MongoClient('mongo', 27017).MLABweb
        print("Prepare >> ", self.db_web)

    def get_current_user(self):
        login = None
        return None

    def get_user_locale(self):
        tornado.locale.set_default_locale("en_UK")
        return self.get_browser_locale()
    


def sendMail(to, subject = "MLAB", text = "No content"):
        message="""From:  MLAB distributed measurement systems <dms@mlab.cz>
To: %s
MIME-Version: 1.0
Content-type: text/html
Subject: %s
""" %(to, subject)
        message += text
        print("-----")
        print(to)
        print(message)
        print("-----")
        smtp = smtplib.SMTP('localhost')
        smtp.sendmail("MLAB distributed measurement systems <dms@mlab.cz>", to, message )
        smtp.close()


def _sql():
    pass
