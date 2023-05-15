#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tornado.escape
from tornado import web
from tornado import websocket
from tornado import options
from . import BaseHandler, sendMail#, _sql
import json
import datetime
import smtplib


import requests

from requests_oauthlib import OAuth2Session

class O_logout(BaseHandler):
    def get(self):
        print("[LOGIN]: Odhlaseni")
        self.clear_cookie("login")
        self.clear_cookie("token")

        self.redirect("/")


class O_login(BaseHandler):
    def get(self):
        login = self.get_secure_cookie("login", None)
        print("[LOGIN]: Login requests by: {}".format(login))

        github = OAuth2Session(options.options.github_token, scope = ["user"])
        authorization_url, state = github.authorization_url('https://github.com/login/oauth/authorize', presmerovani="TEST")

        self.redirect(authorization_url)

class O_github(BaseHandler):
    def get(self):
        print("[LOGIN]: PRESMEROVANI:", self.get_argument('presmerovani', "NIC"))
        github_code = self.get_argument('code', None)
        github = OAuth2Session(options.options.github_token, scope = ["user"])
        token = github.fetch_token('https://github.com/login/oauth/access_token', code = github_code, client_secret=options.options.github_secret)
        user_j = github.get('https://api.github.com/user').json()
        email_j = github.get('https://api.github.com/user/emails').json()
        print('[LOGIN]: GithubLogin', github_code, user_j, email_j)
        user_db = self.db_web.Users.find({"_id":user_j['login']}).count()

        print("[LOGIN]: Token:", token)
        print("[LOGIN]: User:", user_j)
        
        email = None
        for e in email_j:                   # najdi mail, ktery je primarni
            if e['primary'] == True:
                email = e['email']
        print("[LOGIN]: Email:", email)


        self.set_secure_cookie('login', user_j['login'])
        self.set_secure_cookie('token', repr(token))

        utcnow = datetime.datetime.utcnow().isoformat()

        if user_db == 1: # uzivatel je zpet :)
            print("Uzivatel je zpet :)")
            self.db_web.Users.update_one({"_id": user_j['login']},{ "$set": {"email": email, "last_login": datetime.datetime.utcnow()}})
            self.redirect("/")

        elif user_db == 0: # Novy uzivatel
            if not user_j['name']: user_j['name'] = user_j['login']
            print(user_j)
            self.db_web.Users.insert_one({
                "_id": user_j['login'],
                "login": user_j['login'],
                "name": user_j['name'],
                "civil_name": user_j['name'],
                "is_staff": False,
                "email": email,
                "service": "github",
                "date_joined": datetime.datetime.utcnow(),
                "last_login": datetime.datetime.utcnow(),
                "service_data": user_j,
                }
            )

            #TODO: registracni email - není dokoncena sablona pro welcome mail.
            #sendMail("%s<%s>"%(user_j['name'],email),"Welcome to  RTbolidozor", open("/home/roman/repos/RTbolidozor/emails/new_reg","r").read()%(user_j['name']))
            print("[LOGIN]: novy uzivatel")
            self.redirect("/newuser")

        else:
            print("[LOGIN]: Chyba, prosím nahlašte do mailinglistu Bolidozoru GitHub č.0003")
            self.write("[LOGIN]: Chyba, prosím nahlašte do mailinglistu Bolidozoru GitHub č.0003 nebo na email dms@mlab.cz")

class newuser(BaseHandler):
    def get(self):
        self.write("Ahoj, <br> Vítáme Vás na stránkách<a href='/'><b> MLAB </b></a> pokračujte na <a href='/'>hlavní stránku</a>")