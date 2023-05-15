#
#
#   Skript, ktery projde projektove JSON soubory a vlozi je do MONGODB
#
#

import os
import json, yaml
import pymongo
import time


db = pymongo.MongoClient("mongo", 27017)
dbcol = db['MLABweb']['Modules']


for root, dirs, files in os.walk('/data/mlab/Modules/'):
    #print("files", files)
    try:
        for name in files:
            try:
                #print(name)
                if name.endswith((".json")):
                    print("FILE JSON", root, name)
                    #print os.path.join(root, name)
                    
                    json_data=open(os.path.join(root,name)).read()
                    data = json.loads(json_data)
                    id_data = os.path.dirname(root)[19:]
                    
                    print( data)

                    if not data.get('mark', False):
                        data['mark'] = 50

                    if not type(data['category[]']) == list:
                        data['category[]'] = [data['category[]']]

                    dbcol.update_one({"_id":data['name']}, {"$set": data}, upsert=True)
                if 'yaml' in name:
                    print("!!!!!!!!!!1")
                if name == "metadata.yaml":
                    print("FILE yml", root, name)
                    json_data=open(os.path.join(root,name)).read()
                    data = yaml.safe_load(json_data)
                    data['source'] = 'yaml'

                    data['name'] = data['github_repo']

                    if not data.get('mark', False):
                        data['mark'] = 50

                    if not 'category[]' in data: data['category[]'] = []

                    if not type(data['category[]']) == list:
                        data['category[]'] = [data['category[]']]
                    
                    data['status'] = 2
                    data['root'] = ''

                    data['short_cs'] = data['description']
                    data['short_en'] = data['description']
                    data['longname_cs'] = data['description']
                    data['longname_en'] = data['description']
                    data['image'] = data['images']

                    print(data)
                    dbcol.update_one({"_id":data['name']}, {"$set": data}, upsert=True)
            except Exception as e:
                print("CHYBA:", e)

    except Exception as e:
        print("CHYBA:", e)

# while 1:
#     time.sleep(1)
#     print("..")