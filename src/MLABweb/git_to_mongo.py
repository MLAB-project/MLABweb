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
dbcat = db['MLABweb']['Category']


categories = [
    {
        'name': 'Power switches',
        'code': 'power_sw',
        'tags': []
    },{
        'name': 'Sensors',
        'code': 'sensor',
        'tags': []
    },{
        'name': 'Clock',
        'code': 'clock',
        'tags': []
    },{
        'name': 'Radio communication',
        'code': 'comm_rf',
        'tags': []
    },{
        'name': 'IR communication',
        'code': 'comm_ir',
        'tags': []
    },{
        'name': 'Serial communication',
        'code': 'comm_serial',
        'tags': []
    },{
        'name': 'Translators',
        'code': 'translators',
        'tags': []
    },{
        'name': 'Memories',
        'code': 'memory',
        'tags': []
    },{
        'name': 'ARM',
        'code': 'ARM',
        'tags': []
    },{
        'name': 'AVR',
        'code': 'avr',
        'tags': []
    },{
        'name': 'PIC',
        'code': 'pic',
        'tags': []
    },{
        'name': 'Power supply',
        'code': 'power_supply',
        'tags': []
    },{
        'name': 'Universal parts',
        'code': 'universal',
        'tags': []
    },{
        'name': 'Human interfaces',
        'code': 'human_interfaces',
        'tags': []
    },{
        'name': 'Audio',
        'code': 'audio',
        'tags': []
    },{
        'name': 'Motor drivers',
        'code': 'h_bridge',
        'tags': []
    },{
        'name': 'x86 CPU',
        'code': 'x86',
        'tags': []
    },{
        'name': 'Boxes',
        'code': 'boxes',
        'tags': []
    },{
        'name': 'Operational amplifiers',
        'code': 'op_amps',
        'tags': []
    },{
        'name': 'Time-to-digital converters',
        'code': 'tdc',
        'tags': []
    },{
        'name': 'Measuring',
        'code': 'measuring',
        'tags': []
    },{
        'name': 'CPLD FPGA',
        'code': 'cpld_fpga',
        'tags': []
    },{
        'name': 'AD converters',
        'code': 'ad_converters',
        'tags': []
    },{
        'name': 'Mechanical parts',
        'code': 'mechanical',
        'tags': []
    }
]


dbcat.delete_many({})
dbcol.delete_many({})

for c in categories:
    c['_id'] = c['code']
    dbcat.update_one({'_id': c['_id']}, { "$set": c }, upsert=True)


while 1:
    #dbcol.delete_many({})

    #for root, dirs, files in os.walk('/data/mlab/modules-org'):
    for root, dirs, files in os.walk('/data/mlab/Modules'):
        
        if 'assets' in root:
            continue
        if '.git' in root:
            continue
        if 'hw' in root:
            continue
        #print("files", files)
        #print(root)
        try:
            for name in files:
                try:
                    #print(name)
                    if name.endswith((".json")):
                        #print("FILE JSON", root, name)
                        #print os.path.join(root, name)
                        
                        json_data=open(os.path.join(root,name)).read()
                        data = json.loads(json_data)
                        data['source'] = 'legacy'
                        id_data = os.path.dirname(root)[19:]
                        
                        #print( data)

                        if not data.get('mark', False):
                            data['mark'] = 50

                        if not type(data['category[]']) == list:
                            data['category[]'] = [data['category[]']]

                        if not data.get('image_title'):
                            data['image_title'] = data['image']
                        
                        data['github_url'] = 'https://github.com/MLAB-project/Modules/master/{}'.format(data['root'])
                        data['github_raw'] = 'https://raw.githubusercontent.com/MLAB-project/Modules/master/{}'.format(data['root'])

                        data['revisions'] = [data['name']]

                        out = dbcol.find_one({'_id':data['name']})
                        if not out or not out.get('source') == 'yaml':
                            dbcol.update_one({"_id":data['name']}, {"$set": data}, upsert=True)
                            print("json", root)
                        else:
                            print("Preskakuji")

                    #if 'yaml' in name:
                    #    print("!!!!!!!!!!", name)

                    if name == "metadata.yaml":
                        print("yaml", root)
                        json_data=open(os.path.join(root,name)).read()
                        data = yaml.safe_load(json_data)
                        data['source'] = 'yaml'

                        data['name'] = data['github_repo']
                        data['root'] = root
                        data['local_root'] = os.path.abspath(os.path.join(root, '..'))
                        data['file_readme'] = os.path.abspath(os.path.join(root, '..', 'README.md'))

                        if not data.get('mark', False):
                            data['mark'] = 50

                        if not 'category[]' in data: data['category[]'] = []

                        if not type(data['category[]']) == list:
                            data['category[]'] = [data['category[]']]
                        
                        data['status'] = 2
                        data['root'] = ''

                        data['github_raw'] = data.get("github_url", "").replace("github.com","raw.githubusercontent.com")+"/{}/".format(data.get('github_branch'))

                        data['short_cs'] = data['description']
                        data['short_en'] = data['description']
                        data['longname_cs'] = data['description']
                        data['longname_en'] = data['description']
                        
                        if not 'image' in data:
                            data['image'] = data['images'][0]

                        if not data.get('image_title'):
                            data['image_title'] = data['image']

                        #print(data)
                        data['revisions'] = data.get('github_branches', [])
                        for b in data.get('github_branches',[]):
                            print("DELETING ... b")
                            dbcol.delete_one({"_id":b})
                        dbcol.update_one({"_id":data['name']}, {"$set": data}, upsert=True)
                except Exception as e:
                    print("CHYBA:", e, root)
                    repr(e)

        except Exception as e:
            print("CHYBA:", e, root)
        
    for module in dbcol.find({'source': 'legacy'}):
        possible = module['name'][:-1]
        print(module['name'], possible)

        module_revisions = list(dbcol.find({"revisions": module['name']}))
        if len(module_revisions):
            print("SHODA...", possible, module_revisions[0]['name'])

    print("DONE... ")
    time.sleep(300)
    # while 1:
    #     time.sleep(1)
    #     print("..")
