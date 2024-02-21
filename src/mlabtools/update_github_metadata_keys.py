
import requests
import base64
import yaml
import json
import sys

# Your GitHub authentication token is passed as a command-line argument
if len(sys.argv) < 2:
    print("Usage: python3 update_github_metadata_keys.py  YOUR_GITHUB_TOKEN")
    sys.exit(1)

GITHUB_TOKEN = sys.argv[1]

# Common GitHub API headers
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# Load modules.json data (this should be read from an actual JSON file in a real implementation)
modules_json_data = json.load(open('modules.json', 'r'))
#modules_json_data = [{"name": "GPS02", "status": 2}]  # Simplified example data

def get_yaml_from_repo(module_name):
    repo_url = f"https://api.github.com/repos/mlab-modules/{module_name}/contents/doc/metadata.yaml"
    response = requests.get(repo_url, headers=HEADERS)
    if response.status_code == 200:
        file_content_base64 = response.json()['content']
        file_sha = response.json()['sha']
        return base64.b64decode(file_content_base64).decode('utf-8'), file_sha
    else:
        print(f"Failed to get metadata.yaml for {module_name}")
        return None, None

def update_yaml_in_repo(module_name, updated_yaml_content, sha):
    repo_url = f"https://api.github.com/repos/mlab-modules/{module_name}/contents/doc/metadata.yaml"
    data = {
        "message": "Update image to image_title",
        "content": base64.b64encode(updated_yaml_content.encode('utf-8')).decode('utf-8'),
        "sha": sha
    }
    response = requests.put(repo_url, headers=HEADERS, json=data)
    if response.status_code == 200:
        print(f"Successfully updated metadata.yaml for {module_name}")
    else:
        print(f"Failed to update metadata.yaml for {module_name}")

for module in modules_json_data:
    module_name = module['name']
    
    yaml_content, yaml_sha = get_yaml_from_repo(module_name)
    if yaml_content:
        yaml_data = yaml.safe_load(yaml_content)
        if 'image' in yaml_data:
            yaml_data['image_title'] = yaml_data.pop('image')
            updated_yaml_content = yaml.safe_dump(yaml_data)
            update_yaml_in_repo(module_name, updated_yaml_content, yaml_sha)
        elif 'image_title' in yaml_data:
            print(f"image_title already exists for {module_name}.")
