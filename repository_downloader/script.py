import os
import subprocess
import requests
import json
from pymongo import MongoClient
import yaml

# Získání proměnných z systémových proměnných
ORGANIZATION = os.environ.get('ORGANIZATION', "mlab-modules")
LOCAL_REPO_PATH = os.environ.get('LOCAL_REPO_PATH', '/data/mlab/mlab-modules/')
MONGODB_CONNECTION_STRING = os.environ.get('MONGODB_CONNECTION_STRING', 'mongodb://mongo:27017')
MONGODB_DATABASE = os.environ.get('MONGODB_DATABASE', 'MLABweb')
MONGODB_COLLECTION = os.environ.get('MONGODB_COLLECTION', "Modules")
CATEGORIES_FILE = "categories.txt"

# Získání seznamu repozitářů organizace
def get_organization_repositories():
    url = f'https://api.github.com/orgs/{ORGANIZATION}/repos'
    print(url)
    response = requests.get(url)
    repositories = json.loads(response.text)
    return repositories

# Stažení repozitáře
def clone_repository(repo_url, repo_name):
    repo_path = os.path.join(LOCAL_REPO_PATH, repo_name)
    print(repo_url, "->", repo_path)
    if not os.path.exists(repo_path):
        subprocess.call(['git', 'clone', repo_url, repo_path])

# Kontrola smazaných repozitářů
def check_deleted_repositories(repositories):
    local_repos = os.listdir(LOCAL_REPO_PATH)
    for repo in local_repos:
        if repo not in [r['name'] for r in repositories]:
            repo_path = os.path.join(LOCAL_REPO_PATH, repo)
            print(f'Repozitář {repo} byl smazán na GitHubu.')
            subprocess.call(['rm', '-rf', repo_path])

# Nahrání informací do MongoDB
def upload_to_mongodb(repositories):
    client = MongoClient(MONGODB_CONNECTION_STRING)
    db = client[MONGODB_DATABASE]
    collection = db[MONGODB_COLLECTION]

    for repo in repositories:
        try:
            repo_path = os.path.join(LOCAL_REPO_PATH, repo['name'])


            print(repo_path)
            #print(repo)

            json_data=open(os.path.join(repo_path,'doc','metadata.yaml')).read()
            data = yaml.safe_load(json_data)

            data['name'] = data['github_repo']
            #data['root'] = root
            data['local_root'] = repo_path
            data['file_readme'] = os.path.abspath(os.path.join(repo_path, 'README.md'))


            if not data.get('mark', False):
                data['mark'] = 50

            #if not 'category[]' in data: data['category[]'] = []

            #if not type(data['category[]']) == list:
            #    data['category[]'] = [data['category[]']]
            
            data['status'] = 2
            data['root'] = ''

            data['github_raw'] = data.get("github_url", "").replace("github.com","raw.githubusercontent.com")+"/{}/".format(data.get('github_branch'))

            data['short_en'] = data['description']
            data['longname_en'] = data['description']
            
            if not 'image' in data and 'images' in data:
                if len(data['images']):
                    data['image'] = data['images'][0]

            if not data.get('image_title') and 'image' in data:
                data['image_title'] = data['image']

            collection.insert_one(data)
        except Exception as e:
            print(e)

    client.close()

# Získání kategorie repozitáře
def get_category(repo_name):
    with open(CATEGORIES_FILE, 'r') as file:
        categories = file.read().splitlines()

    for category in categories:
        if repo_name.startswith(category):
            return category

    return 'N/A'


# Synchronizace větví
def sync_branches(repositories):
    for repo in repositories:
        try:
            repo_path = os.path.join(LOCAL_REPO_PATH, repo['name'])
            if os.path.exists(repo_path):
                os.chdir(repo_path)
                subprocess.call(['git', 'checkout', repo['default_branch']])
                subprocess.call(['git', 'pull'])
        except Exception as e:
            print(e)

# Hlavní funkce
def main():
    repositories = get_organization_repositories()[:3]
    print("Repositories:")
    print(len(repositories))
    for repo in repositories:
        clone_repository(repo['clone_url'], repo['name'])
    sync_branches(repositories)
    check_deleted_repositories(repositories)
    upload_to_mongodb(repositories)

if __name__ == '__main__':
    main()
