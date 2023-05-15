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
        login = self.get_secure_cookie("login")
        token = self.get_secure_cookie("token")

        try:
        	self.db_web
        except Exception as e:
        	print("Bezpecnostni procedura.... ")
        	self.db_web = pymongo.MongoClient('mongo', 27017).MLABweb
        
        if not login:
            print("neni prihlasen")
            return None
        else:
            print("_id", login)
            user = self.db_web.Users.find_one({"_id": login})
    
            print("Logen in", user['civil_name'])
            return user

    def get_user_locale(self):
        if not self.get_cookie("locale"):
            #print "Locale neni nastaveno - nastavuji en_UK"
            tornado.locale.set_default_locale("en_UK")
            return self.get_browser_locale()

        locale =  self.get_cookie("locale")
        #print "locale:", locale
        tornado.locale.set_default_locale(locale)
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
