#!/usr/bin/python
# -*- coding: utf-8 -*-

import tornado
import json
from bson.json_util import dumps
import datetime
import glob
import glob2
import shutil
import time
#from tornado import web
#from tornado import ioloop
#from tornado import auth
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

import markdown

#import subprocess

def assembly_gh_link(document):
    if document.get('source', None) == 'yaml':
        url = document.get('github_url', '')
        url += '/tree/'
        url += document.get('github_branch', '')

        return url
    
    else:
        return "https://github.com/MLAB-project/Modules/tree/master/" + document.get('root', '')

class permalink(BaseHandler):
    #@asynchronous
    def get(self, module = None):
        print(module)
        module_data = self.db_web.Modules.find({"_id": module})[0]
        documents = glob2.glob(tornado.options.options.mlab_repos+module_data['root']+"//**/*.pdf")
        images = glob.glob(tornado.options.options.mlab_repos+module_data['root']+"doc/img/*")
        self.render("modules.detail.hbs", module=module, module_data=module_data, images = images, documents=documents, assembly_gh_link = assembly_gh_link)

class home(BaseHandler):
    #@asynchronous
    def get(self, data=None):
        module_data = self.db_web.Modules.find(
            { "$or": [{
                        "$and": [ 
                            {'homepage': {"$eq": True}},
                            {"$where": "this.image_title.length > 4"},
                            {'image_title':{"$not":re.compile("QRcode")}}
                        ]
                    },
                    {
                        "$and": [ 
                            {"$or":[{'status': 2}, {'status':'2'}]},
                            {'mark': {"$gte": 55}},
                            {"$where": "this.image_title.length > 4"},
                            {'image_title':{"$not":re.compile("QRcode")}}
                        ]
                    },
                    {
                        "$and": [ 
                            {"$or":[{'status': 2}, {'status':'2'}]},
                            {'homepage': {"$eq": 1}},
                            {"$where": "this.image_title.length > 4"},
                            {'image_title':{"$not":re.compile("QRcode")}}
                        ]
                    }
                ],
            }
        )

        self.render("index.hbs", parent=self, modules = module_data)

class ibom(BaseHandler):
    #@asynchronous
    def get(self, module = None):
        print(module)
        module_data = self.db_web.Modules.find({"_id": module})[0]

        self.render(module_data['local_root']+'/'+module_data['mod_ibom'])

        
class readme(BaseHandler):
    #@asynchronous
    def get(self, module = None):
        print(module)
        #if ''
        module_data = self.db_web.Modules.find({"_id": module})[0]



class module_detail(BaseHandler):
    #@asynchronous
    def get(self, module = None):
        print(module)

        module_revisions = list(self.db_web.Modules.find({"github_branches": module}))
        if len(module_revisions):
            nn = module[:-1]
            if len(list(self.db_web.Modules.find({"name": nn}))):
                self.redirect("/module/{}/".format(nn))
        
        module_data = self.db_web.Modules.find({"_id": module})[0]
        module_path = tornado.options.options.mlab_repos+module_data['root']

        images = glob.glob(module_path+"/doc/img/*.jpg")
        images.extend(glob.glob(module_path+"/doc/img/*.png"))
        images.extend(glob.glob(module_path+"/doc/img/*.svg"))

        if not module_data.get('file_readme'):
            readme_html = "No content"
        else:
            readme_html = markdown.markdown(open(module_data.get('file_readme', ''), 'r').read(),
                extensions=['pymdownx.extra', 'pymdownx.magiclink', 'pymdownx.b64'],
                extension_configs={
                    "pymdownx.b64": {"base_path": os.path.dirname(module_data.get('file_readme', ''))},
                }
            )

        self.render("modules.detail.hbs", db_web = self.db_web, module=module, module_data=module_data, images = images, documents = glob2.glob(module_path+"//**/*.pdf"),
            assembly_gh_link = assembly_gh_link, readme_html = readme_html, path = module_path)

class module_comapare(BaseHandler):
    #@asynchronous
    def get(self, module = None):
        print(module, "< compare")
        module_data = _sql("SELECT * FROM MLAB.Modules WHERE name='%s'" %(module))[0]

        doc_cs = open(tornado.options.options.mlab_repos+module_data['root']+'/doc/src/module.cs.html').read()
        doc_en = open(tornado.options.options.mlab_repos+module_data['root']+'/doc/src/module.en.html').read()
        self.render("modules.compare.hbs", _sql=_sql, module=module, module_data=module_data, doc_cs=doc_cs, doc_en=doc_en)

class categories(BaseHandler):
    def get(self):
        categories = self.db_web.Category.find()
        self.render("categories.edit.hbs", categories = categories)
    


class modules(BaseHandler):
    def make_list(self, input):
        print(input)
        if isinstance(input, list): return input
        else: return [input]

    #@asynchronous
    def get(self, category = None):
        print("[MODULES] {}".format(category))
        status = []
        statuss = []

        if 'status' in self.request.arguments:
            status = self.request.arguments['status']
            s = []
            for st in status:
                if(len(st)):
                    for sta in st.decode('utf-8').split(','):
                        s.append(int(sta))
            #status = [int(n.decode("utf-8")) for n in ]
            status = s

        else:
            status = self.get_cookie('status', "2").split(",")
            status = [int(n) for n in status]


        status = status + statuss

        #print "status", status
        #print "category", category
        search = self.get_argument('search', '');
        print("search:", search)


        if category:
            cat_pol = "$in"
        else:
            cat_pol = "$nin"

        if not len(search):

            q = [
                {
                    "$unwind": "$_id"
                }]
            if category:
                q += [
                    {
                        "$match": {'category[]': {cat_pol: [category]}}
                    }]
            q += [
                {
                    "$match": {'status': {"$in": status}}
                },
                {
                    "$match": {"$or": [
                        {
                            "name": { "$regex": search, "$options": 'i'}
                        },
                        {
                            'description': { "$regex": search, "$options": 'i'}
                        }
                    ]}
                }
            ]
            modules = self.db_web.Modules.aggregate(q)
        else:
            modules = self.db_web.Modules.aggregate([
               
                {
                    "$match": {"$or": [
                        {
                            "name": { "$regex": search, "$options": 'i'}
                        },
                        {
                            'description': { "$regex": search, "$options": 'i'}
                        }
                    ]}
                }
            ])

        self.render("modules.hbs", parent=self, category = category, modules = modules, status = status, db_web = self.db_web, search_query=search)


    def post(self, category = None):
        print(self.request.arguments)
        print("Modules - POST")
        print("cat:", category)
        search = self.get_argument('search', '');
        print("search:", search)
        modules = self.db_web.Modules.aggregate([
            {
                "$unwind": "$_id"
            },
            {
                "$match": {"$or": [
                    {
                        "name": { "$regex": search, "$options": 'i'}
                    },
                    {
                        'short_en': { "$regex": search, "$options": 'i'}
                    }
                ]
            }
            }

        ])

        self.write(dumps(modules))

class modules_overview(BaseHandler):
    #@asynchronous
    #@tornado.web.authenticated
    def get(self):
        #print("modules overview")
        order = self.get_argument('order', '_id')
        modules = self.db_web.Modules.find().sort([(order, 1)])
        self.render("modules.overview.hbs", parent=self, modules = modules)

class moduleImageUpload(BaseHandler):
    '''
        Tato funkce se stara o prijem uploadovanych obrazku a spravne zarazeni. 
        Nazev modulu je v URL adrese.
        Funkce vrátí seznam obrázků od modulu pro jeho snadnou aktualizaci.
    '''
    def post(self, module):
        self.set_header('Content-Type', 'application/json')
        print("[IMAGE_UPLOAD]")

        module_data = list(self.db_web.Modules.find({'_id': module}))[0]
        
        filename = self.request.files['image'][0]['filename']

        output_file = open(tornado.options.options.mlab_repos+module_data['root']+"/doc/img/"+filename, 'wb')
        output_file.write(self.request.files['image'][0]['body'])
        output_file.close()

        images = glob.glob(tornado.options.options.mlab_repos+module_data['root']+"/doc/img/*")
        
        for i, image in enumerate(images):
            images[i] = {
                        'local':image[len(tornado.options.options.mlab_repos)+len(module_data['root']):],
                        'url': '/repos/'+image[len(tornado.options.options.mlab_repos):]
                        }


        repo = Repo(tornado.options.options.mlab_repos)
        repo.index.add([module_data['root']])
        
        if self.current_user:
            author = Actor(self.current_user['_id'], self.current_user['email'])
        else:
            author = Actor("Anonymn", "dms@mlab.cz")
        repo.index.commit("[MLABweb] new image", author=author, committer=author)

        output = json.dumps(images)
        self.write(output)



class module_edit(BaseHandler):
    @tornado.web.authenticated
    #@asynchronous
    def get(self, module=None):
        directories = set()
        if module:
            new = False
            module_data = self.db_web.Modules.find_one({"_id": module})
            images = glob.glob(tornado.options.options.mlab_repos+module_data['root']+"/doc/img/*")
        else:
            new = True
            path = glob2.glob(os.path.join(tornado.options.options.mlab_repos, '**/*.json'))
            crop = len(tornado.options.options.mlab_repos)
            for p in path:
                directories.add('/'.join(p[crop:].split('/')[:-2]))
            print("[EDIT]", directories)
            module_data = {
                'status': 1,
            }
            images = []

        self.render("modules.edit.hbs", parent=self, module_data=module_data, images = images, db_web = self.db_web, all = True, new = new, directories = list(directories))
    
    def make_list(self, input):
        if isinstance(input, list): return input
        else: return [input]

    @tornado.web.authenticated
    def post(self, module=None):
        modules_root = tornado.options.options.mlab_repos

        module = self.get_argument('name').strip()
        print("[EDIT][POST]:", module)

        # pokud slozka neexistuje vytvorit novou
        if not os.path.isfile(os.path.join(modules_root, self.get_argument('root', ''), module+'.json')):
            print("Slozka pro tento modul - vytvarim ji")
            shutil.copytree(tornado.options.options.mlabgen+'module', tornado.options.options.mlab_repos+self.get_argument('root'))
            for root, dirs, files in os.walk(tornado.options.options.mlab_repos+self.get_argument('root') , topdown=False):
                for file in files:
                    if 'module' in file:
                        print(root, file)
                        if not any(s in file for s in ['kicad_wks']):
                            shutil.move(root+"/"+file, root+"/"+file.replace('module', self.get_argument('name')))

        image_path = str(self.get_argument('image', '')).strip()
        print("IMAGE PATH", image_path)
        if image_path == '':
            image_path = "/doc/img/"+module+"_QRcode.png"
        print("Image path NEW", image_path)
        #image_small = (os.path.splitext(self.get_argument('image'))[0]+'.jpgs').strip()

        print(self.request.arguments)

        self.db_web.Modules.update_one(
            {"_id": self.get_argument('name').strip()},

            { "$set":{
                "name": self.get_argument('name').strip(),
                "root": self.get_argument('root').strip(),
                "wiki": self.get_argument('wiki').strip(),
                "ust": self.get_argument('ust').strip(),
                "longname_cs": self.get_argument('longname_cs'),
                "longname_en": self.get_argument('longname_en'),
                "short_cs": self.get_argument('short_cs'),
                "short_en": self.get_argument('short_en'),
                "doc_cs": self.get_argument('doc_cs'),
                "doc_en": self.get_argument('doc_en'),
                "image": image_path,
                "image_small": image_path,
                "status": int(self.get_argument('status').strip()),
                "mark": float(self.get_argument('mark').strip()),
                "author[]": self.make_list(self.get_arguments('author[]')),
                "category[]": self.make_list(self.get_arguments('category[]')),
                "parameters": eval(self.get_argument('parameters', "[]"))
            }},
            upsert = True
        )

        # ulozeni json soboru ze zmenenych dat
        # nacteni dat z DB
        db_data = self.db_web.Modules.find_one({"_id": self.get_argument('name').strip()})
        module_json_path = tornado.options.options.mlab_repos+db_data['root']+'/' + module + '.json'
        module_qr_path = tornado.options.options.mlab_repos+db_data['root']+'/doc/img/' + module + '_QRcode.png'

        # ulozeni dat do json souboru
        file_content = json.dumps(db_data, indent=4, ensure_ascii=False).encode('utf8')
        with open(module_json_path, "w") as text_file:
            text_file.write(file_content)

        # vytvoreni slozky /doc/img, pokud jeste neexistuje
        try: os.makedirs(tornado.options.options.mlab_repos+db_data['root'] + '/doc/img')
        except Exception as e: pass

        # pokud neexistuje QR, tak ho vytvorit
        if not os.path.isfile(module_qr_path):
            try:
                print("QR neexistuje, asi by jsi ho mel vytvorit")
                qr = qrcode.QRCode( version=4, error_correction=qrcode.constants.ERROR_CORRECT_Q, box_size=15, border=4)
                qr.add_data('https://www.mlab.cz/PermaLink/'+module)
                qr.make(fit=True)
                qr.make_image().save(module_qr_path)
            except Exception as e: pass


        #Generovani README.md
        data = {
            'time': datetime.datetime.now(),
            'date': datetime.datetime.now().date(),
            'autor': '',
            'email': '',
            'tags': '',
            'ust': '',
            'module': self.get_argument('name').strip(),
            'subtitle': self.get_argument('longname_en'),
            'describe': self.get_argument('short_en'),
            'img': image_path[1:]
        }
        readme = self.render_string("documents/module.readme.md", **data)

        output_file = open(tornado.options.options.mlab_repos+db_data['root']+"/README.md", 'wb')
        output_file.write(readme)
        output_file.close()


        #try:
        #    im = Image.open(tornado.options.options.mlab_repos+self.get_argument('root')+self.get_argument('image'))
        #    im.thumbnail((512,512), Image.ANTIALIAS)
        #    im.save(tornado.options.options.mlab_repos+self.get_argument('root')+image_small, 'JPEG', quality=65)
        #except Exception as e: pass


        '''

        text_file = open(tornado.options.options.mlab_repos+self.get_argument('root')+'/README.md', "w")
        text_file.write(
            """
[Czech](./README.cs.md)
<!--- module --->
# %(module)s
<!--- Emodule --->

<!--- subtitle --->%(subtitle)s<!--- Esubtitle --->

![%(module)s](%(image)s)

<!--- description --->%(text)s<!--- Edescription --->
            """ %{'module':data_json['name'], 'image':data_json['image'], 'subtitle':data_json['longname_en'], 'text':data_json['short_en']})
        text_file.close()

        text_file = open(tornado.options.options.mlab_repos+self.get_argument('root')+'/README.cs.md', "w")
        text_file.write(
            """
[English](./README.md)
<!--- module --->
# %(module)s
<!--- Emodule --->

<!--- subtitle --->%(subtitle)s<!--- Esubtitle --->

![%(module)s](%(image)s)

<!--- description --->%(text)s<!--- Edescription --->
            """ %{'module':data_json['name'], 'image':data_json['image'], 'subtitle':data_json['longname_cs'], 'text':data_json['short_cs']})
        text_file.close()


        html_content = replace_entities(data_json['doc_cs']).encode('UTF-8')

        html =  """
<html>
<head>
    <meta charset="UTF-8">
    <title>%(module)s</title>
    <meta name="generator" content="pandoc" />
    <meta name="subtitle" content="%(subtitle)s"/>
    <meta name="author" content="%(author)s"/>
    <meta name="TopImage" content="/home/roman/repos/Modules/OpAmps/OZDUAL02B/DOC/SRC/img/OZDUAL02B_Top_Big.JPG"/>
    <meta name="QR" content="/home/roman/repos/Modules/OpAmps/OZDUAL02B/DOC/SRC/img/OZDUAL02B_QRcode.png"/>
    <meta name="abstract" content="%(abstract)s"/>

<style>
</style>
<head>
<body>
    
    %(doc)s

</body>
</html>

                """ %{'module':data_json['name'],'subtitle':data_json['longname_cs'], 'doc':html_content, 'author':"Autor 1, Autor 2", 'abstract':data_json['short_cs']}
        #print html

        #text_file = open(tornado.options.options.mlab_repos+data['root'][0]+'/DOC/SRC/module.cs.html', "w")
        #text_file.write(html)
        #text_file.close()





        html_content = replace_entities(data_json['doc_en']).encode('UTF-8')

        html =  """
<html>
<head>
    <meta charset="UTF-8">
    <title>%(module)s</title>
    <meta name="generator" content="pandoc" />
    <meta name="subtitle" content="%(subtitle)s"/>
    <meta name="author" content="%(author)s"/>
    <meta name="TopImage" content="/home/roman/repos/Modules/OpAmps/OZDUAL02B/DOC/SRC/img/OZDUAL02B_Top_Big.JPG"/>
    <meta name="QR" content="/home/roman/repos/Modules/OpAmps/OZDUAL02B/DOC/SRC/img/OZDUAL02B_QRcode.png"/>
    <meta name="abstract" content="%(abstract)s"/>

<style>
</style>
<head>
<body>
    
    %(doc)s

</body>
</html>

                """ %{'module':data_json['name'],'subtitle':data_json['longname_en'], 'doc':html_content, 'author':"Autor 1, Autor 2", 'abstract':data_json['short_en']}
        #print html

        #text_file = open(tornado.options.options.mlab_repos+data['root'][0]+'/DOC/SRC/module.en.html', "w")
        #text_file.write(html)
        #text_file.close()
        '''


        #process = subprocess.Popen(["pandoc", "-s", tornado.options.options.mlab_repos+data['root'][0]+'/DOC/SRC/module.cs.html', "-o", tornado.options.options.mlab_repos+data['root'][0]+'/DOC/'+data_json['name']+'.cs.pdf', "--template=/home/roman/repos/test-mlab-ui/src/MLABweb/template/doc.en.latex"])
        #process = subprocess.Popen(["pandoc", "-s", tornado.options.options.mlab_repos+data['root'][0]+'/DOC/SRC/module.en.html', "-o", tornado.options.options.mlab_repos+data['root'][0]+'/DOC/'+data_json['name']+'.en.pdf', "--template=/home/roman/repos/test-mlab-ui/src/MLABweb/template/doc.en.latex"])
        

        repo = Repo(tornado.options.options.mlab_repos)
        repo.index.add([self.get_argument('root')])
        
        if self.current_user:
            author = Actor(self.current_user['_id'], self.current_user['email'])
        else:
            author = Actor("Anonymn", "dms@mlab.cz")
        repo.index.commit("[MLABweb] %s; %s" %(self.get_argument('commit_msg', "Documentation edits"), self.get_argument('name', "MODULE")), author=author, committer=author)



