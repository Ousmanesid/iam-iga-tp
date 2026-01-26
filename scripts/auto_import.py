import os
import requests
import glob
from requests.auth import HTTPBasicAuth

MIDPOINT_URL = "http://localhost:8080/midpoint/ws/rest"
AUTH = HTTPBasicAuth("administrator", "5ecr3t")
HEADERS = {"Content-Type": "application/xml"}

def import_file(filepath, category):
    print(f"Importing {filepath}...")
    with open(filepath, 'rb') as f:
        data = f.read()
    
    # On utilise l'endpoint générique /objects avec l'option overwrite
    url = f"{MIDPOINT_URL}/objects?options=overwrite"
    
    try:
        response = requests.post(url, auth=AUTH, headers=HEADERS, data=data)
        if response.status_code in [200, 201, 204, 240, 250]:
            print(f"  ✓ Success ({response.status_code})")
        else:
            print(f"  ✗ Failed ({response.status_code})")
            print(f"    Response: {response.text[:200]}")
    except Exception as e:
        print(f"  Err: {e}")

def main():
    base_path = "/root/iam-iga-tp/config/midpoint"
    
    # Ordre d'import important
    folders = [
        ("resources", "resources"),
        ("roles", "roles"),
        ("object-templates", "objectTemplates"),
        ("tasks", "tasks")
    ]
    
    for folder, cat in folders:
        path = os.path.join(base_path, folder, "*.xml")
        files = glob.glob(path)
        for f in sorted(files):
            import_file(f, cat)

if __name__ == "__main__":
    main()
