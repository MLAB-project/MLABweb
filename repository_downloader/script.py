import os
import subprocess
import requests
import json
from pymongo import MongoClient
import yaml
import time

# Získání proměnných z systémových proměnných
ORGANIZATION = os.environ.get('ORGANIZATION', "mlab-modules")
LOCAL_REPO_PATH = os.environ.get('LOCAL_REPO_PATH', '/data/mlab/mlab-modules/')
MONGODB_CONNECTION_STRING = os.environ.get('MONGODB_CONNECTION_STRING', 'mongodb://mongo:27017')
MONGODB_DATABASE = os.environ.get('MONGODB_DATABASE', 'MLABweb')
MONGODB_COLLECTION = os.environ.get('MONGODB_COLLECTION', "Modules")
CATEGORIES_FILE = "categories.txt"

# Získání seznamu repozitářů organizace
def get_organization_repositories():

    # Fetch repositories in paginated manner
    # Determine the total number of repositories in the organization
    response = requests.get(f"https://api.github.com/orgs/{ORGANIZATION}")
    if response.status_code != 200:
        print(f"Failed to fetch organization info: {response.content}")
        sys.exit(1)
    total_repos = response.json().get("public_repos", 0)  # Change this to 'total_repos' if you are considering private repos as well

    # Calculate the number of pages needed
    pages_needed = -(-total_repos // 100)  # Equivalent to math.ceil(total_repos / 100)


    # Fetch repositories in a paginated manner considering the total number of repositories
    repositories = []
    for page in range(1, pages_needed + 1):
        url = f'https://api.github.com/orgs/{ORGANIZATION}/repos?per_page=100&page={page}'
        print(url)
        response = requests.get(url)
        if response.status_code != 200:
            print(f"Failed to fetch page {page}: {response.content}")
            break
        repositories += json.loads(response.text)
        time.sleep(2)
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

    collection.delete_many({})

    for repo in repositories:
        try:

            if repo['name'] in ['MODUL01', '.github']:
                print("Tento modul nebudu ukladat do databaze")
                continue

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
                data['mark'] = 30
            
            data['homepage'] = data.get('homepage', False)
            data['description'] = data.get('description', '')
            
            if not data.get('status', False):
                data['status'] = 0
            data['root'] = ''

            data['github_raw'] = data.get("github_url", "").replace("github.com","raw.githubusercontent.com")+"/{}/".format(data.get('github_branch'))

            data['short_en'] = data['description']
            data['longname_en'] = data['description']

            if data.get('replaced'):
                data['status'] = 3
                data['homepage'] = False
            
            if not data.get('image_title'):
                if len(data['images']):
                    data['image_title'] = data['images'][0]

            #collection.insert_one(data)
            collection.update_one({"_id":data['name']}, {"$set": data}, upsert=True)
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
    repositories = get_organization_repositories()
    print("Repositories:")
    print(len(repositories))
    for repo in repositories:
        clone_repository(repo['clone_url'], repo['name'])
    sync_branches(repositories)
    check_deleted_repositories(repositories)
    upload_to_mongodb(repositories)

if __name__ == '__main__':
    main()
