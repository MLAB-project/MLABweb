#!/usr/bin/python
# -*- coding: utf-8 -*-
import tornado
#from tornado import web
from tornado import ioloop
from tornado import auth
from tornado import escape
from tornado import httpserver
from tornado import options
from tornado import web

import httplib2
import json
import base64
import os

from . import _sql, BaseHandler, sendMail


class webhooks(BaseHandler):
    def post(self):
        webhook = json.loads(self.request.body)
        #print(json.dumps(webhook, indent=4))
        print("======================")
        print("author:", webhook['commits'][0]['author']['username'])
        print("added:", webhook['commits'][0]['added'])
        print("modified:", webhook['commits'][0]['modified'])

        edits = webhook['head_commit']['added'] + webhook['head_commit']['modified']

        if '[MLABweb]' in webhook['head_commit']['message']:
            print("preskakuji pouziti tohoto commitu, protoze jsem ho vytvoril ja...")
            self.write("ACK - skipped, my own commit")
        else:

            project_file =  None
            for edit in edits:
                print(edit)
                if '.json' in edit:
                    print( "Tady je ASI nejaky upraveny nebo novy modul :)")
                    project_file = edit
                    #project_name = os.path.splitext(os.path.basename(edit))[0]
                    project_name = os.path.basename(os.path.dirname(edit))
                    project_root = os.path.split(edit)[0]
                    print(project_file, project_name)
                    try:
                        print( 'url', "https://api.github.com/repos/MLAB-project/Modules/contents/"+project_file+"?ref=master")
                        resp, content = httplib2.Http().request("https://api.github.com/repos/MLAB-project/Modules/contents/"+project_file+"?ref=master")

                        file = json.loads(base64.b64decode(json.loads(content)['content']))
                        print( json.dumps(file, indent=4, sort_keys=True))

                        modules = self.db_web.Modules.find({"_id": project_name}).count()
                        #print ("MODULES:", modules, "(0 novy modul, 1 Existujici modul)")
                        print( ("MODULES:", modules))

                        file['root'] = project_root
                        file['name'] = project_name
                        self.db_web.Modules.update({"_id": project_name}, file, upsert=True)
                        
                        #if modules == 0:
                        #    print "Novy modul"
                        #    self.db_web.Modules
                        #    #_sql("INSERT INTO `MLAB`.`Modules` (`name`, `wiki`, `ust`, `root`, `image`, `longname_cs`, `longname_en`, `short_cs`, `short_en`, `doc_cs`, `status`, `type`) VALUES ('%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s');"
                        #    #    %(project_name, file['wiki'], file['ust'], project_root, file['image'], file['longname_cs'], file['longname_en'], file['short_cs'], file['short_en'], file['doc_cs'], file['status'], '0'))#
                        #
                        #else:
                        #    print "Existujici modul"
                        #    _sql("UPDATE `MLAB`.`Modules` SET `wiki`='%s', `ust`='%s', `image`='%s', `longname_cs`='%s', `longname_en`='%s', `short_cs`='%s', `short_en`='%s', `doc_cs`='%s', `doc_en`='%s', `status`='%s', `root`='%s', `modif`=now() WHERE `name`='%s';" 
                        #        %(file['wiki'], file['ust'], file['image'], file['longname_cs'], file['longname_en'], file['short_cs'], file['short_en'], file['doc_cs'], file['doc_en'], file['status'], project_root, project_name))

                    except Exception as e:
                        print( "chyba>", e)
            
            self.write("ACK")
