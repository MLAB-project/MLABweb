#!/usr/bin/python
# -*- coding: utf-8 -*-
import tornado
from tornado import ioloop
from tornado import options
from tornado import web
import functools
import json
import time
import datetime
import calendar

from handlers import github, admin, auth, api
from handlers import _sql, BaseHandler

tornado.options.define("port", default=5000, help="port", type=int)
tornado.options.define("debug", default=True, help="debug mode")
tornado.options.define("mlab_repos", default='/data/mlab/Modules/', help="Where is MLAB repository stored")
tornado.options.define("mlabgen", default=None, help="Where is mlabgen repository stored")
tornado.options.define("github_token", default=None, help="Github Oauth2 token code")
tornado.options.define("github_secret", default=None, help="Github Oauth2 secret code")


class all(BaseHandler):
    def get(self, arg=None):
        #self.write("ACK")
        self.render("index.hbs", parent=self)


    def post(self, arg=None):
        self.write("ACK")


class WebApp(tornado.web.Application):
    def __init__(self, config={}):

        name = 'MLAB'
        server = 'mlab.cz'

        server_url = '{}:{}'.format(server, tornado.options.options.port)

        handlers =[
            (r'/', admin.home),

            (r'/sitemap.xml', admin.sitemap),
            (r'/robots.txt', admin.robots),

            (r'/module/', admin.modules),
            (r'/module', admin.modules),
            #(r'/module/new', admin.module_edit),
            #(r'/module/edit', admin.module_edit),
            #(r'/module/(.*)/edit/', admin.module_edit),
            #(r'/module/(.*)/edit/', admin.module_edit),
            #(r'/module/(.*)/edit', admin.module_edit),
            #(r'/module/(.*)/edit/upload_image/', admin.moduleImageUpload),
            (r'/module/(.*)/compare/', admin.module_comapare),
            (r'/module/(.*)/compare', admin.module_comapare),
            (r'/module/(.*)/ibom', admin.ibom),
            (r'/module/(.*)/readme', admin.readme),
            (r'/module/(.*)/', admin.module_detail),
            (r'/module/(.*)', admin.module_detail),
            (r'/modules/all', admin.modules_overview),

            (r'/api/modules/', api.modules),
            (r'/api/module/(.*)/', api.module),

            (r'/admin/', admin.home),
            (r'/modules', admin.modules),
            (r'/modules/', admin.modules),
            (r'/modules/(.*)/', admin.modules),
            (r'/modules/(.*)', admin.modules),
            # (r'/admin/module', admin.modules),
            # (r'/admin/modules', admin.modules),
            # (r'/admin/module/', admin.modules),
            # (r'/admin/modules/', admin.modules),
            # (r'/admin/module/new', all),
            # (r'/admin/module/edit(.*)', admin.module_edit),
            #(r'/WebSVN/(.*)', tornado.web.redirect, {'url': 'https://github.com/MLAB-project/Modules', 'permanent': True}),

            (r'/categories/(.*)', admin.categories),
            (r'/categories/', admin.categories),
            (r'/categories', admin.categories),
            #(r'/users', admin.home),

            (r'/PermaLink/(.*)/', admin.permalink),
            (r'/PermaLink/(.*)', admin.permalink),

            #(r'/login/oauth/github', auth.O_github),
            #(r'/login/newuser', auth.newuser),
            #(r'/login/', auth.O_login),
            #(r'/login', auth.O_login),
            #(r'/logout/', auth.O_logout),
            #(r'/logout', auth.O_logout),

            #(r'/git/hook', github.webhooks),

            #staticke soubory je vhodne nahradit pristupem primo z proxy serveru. (pak to tolik nevytezuje tornado)
            (r'/favicon.ico', tornado.web.StaticFileHandler, {'path': "/static/"}),
            (r'/static/(.*)', tornado.web.StaticFileHandler, {'path': 'static/'}),
            (r'/repos/(.*)', tornado.web.StaticFileHandler, {'path': tornado.options.options.mlab_repos}),
            (r'/git/hook/', github.webhooks),
            (r"/(.*)", admin.home),
        ]
        settings = dict(
            cookie_secret="ejuchocrhioke3pkeuipoiiqeuiijeik",
            template_path= "template/",
            static_path= "static/",
            xsrf_cookies=False,
            name=name,
            server_url=server_url,
            site_title=name,
            login_url="/login",
            #ui_modules=modules,
            port=tornado.options.options.port,
            compress_response=True,
            debug=tornado.options.options.debug,
            autoreload=True
        )
        tornado.locale.load_translations("locale/")
        tornado.web.Application.__init__(self, handlers, **settings)

def main():
    import os
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    #tornado.options.parse_config_file("/etc/mlab.conf")
    #tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(WebApp())
    http_server.listen(tornado.options.options.port)
    tornado.ioloop.IOLoop.instance().start()
    #http_server.start(4)

if __name__ == "__main__":
    main()
