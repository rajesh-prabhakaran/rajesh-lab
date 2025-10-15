import json
import os
import requests
from requests.auth import HTTPBasicAuth
import boto3

def get_confluence_credentials(secret_name):
    client = boto3.client('secretsmanager')
    secret = client.get_secret_value(SecretId=secret_name)
    return json.loads(secret['SecretString'])

def fetch_page_metadata(base_url, page_id, auth):
    url = f"{base_url}/wiki/rest/api/content/{page_id}?expand=version,metadata.labels,history"
    headers = {"Accept": "application/json"}
    response = requests.get(url, headers=headers, auth=auth)
    if response.status_code != 200:
        raise Exception(f"Error fetching page metadata: {response.text}")
    return response.json()

def fetch_view_count(base_url, page_id, auth):
    url = f"{base_url}/wiki/rest/api/analytics/content/{page_id}/views"
    headers = {"Accept": "application/json"}
    response = requests.get(url, headers=headers, auth=auth)
    if response.status_code == 200:
        return response.json().get("count", "N/A")
    else:
        print(f"[WARN] View count failed for page {page_id}: {response.status_code}")
        return "Unavailable"

def fetch_child_pages(base_url, parent_id, auth):
    headers = {"Accept": "application/json"}
    url = f"{base_url}/wiki/rest/api/content/{parent_id}/child/page?limit=100&expand=version,metadata.labels,history"
    response = requests.get(url, headers=headers, auth=auth)
    if response.status_code != 200:
        print(f"[WARN] Failed to fetch children of {parent_id}: {response.status_code}")
        return []
    return response.json().get("results", [])

def collect_page_data(base_url, root_id, auth):
    all_pages = []
    queue = [root_id]

    while queue:
        current_id = queue.pop(0)
        try:
            page = fetch_page_metadata(base_url, current_id, auth)
            view_count = fetch_view_count(base_url, current_id, auth)
            page_info = {
                'title': page.get('title'),
                'id': current_id,
                'last_updated': page.get('version', {}).get('when'),
                'version': page.get('version', {}).get('number'),
                'creator': page.get('history', {}).get('createdBy', {}).get('displayName'),
                'labels': [label['name'] for label in page.get('metadata', {}).get('labels', {}).get('results', [])],
                'view_count': view_count
            }
            all_pages.append(page_info)
            children = fetch_child_pages(base_url, current_id, auth)
            queue.extend([child['id'] for child in children])
        except Exception as e:
            print(f"[ERROR] Skipping page {current_id}: {e}")
    return all_pages

def generate_html_table(page_data):
    html = "<h2>Confluence Page Analytics Report</h2>"
    html += "<table border='1' cellpadding='5' cellspacing='0'>"
    html += "<tr><th>Title</th><th>Last Updated</th><th>Version</th><th>Creator</th><th>Labels</th><th>View Count</th></tr>"
    for page in page_data:
        html += f"<tr><td>{page['title']}</td><td>{page['last_updated']}</td><td>{page['version']}</td><td>{page['creator']}</td><td>{', '.join(page['labels'])}</td><td>{page['view_count']}</td></tr>"
    html += "</table>"
    return html

def update_confluence_page(base_url, page_id, auth, html_content):
    # Fetch current version and space key
    headers = {"Accept": "application/json"}
    url = f"{base_url}/wiki/rest/api/content/{page_id}?expand=version,space"
    response = requests.get(url, headers=headers, auth=auth)
    if response.status_code != 200:
        raise Exception(f"Error fetching target page version: {response.text}")
    page = response.json()
    current_version = page['version']['number']
    title = page['title']
    space_key = page['space']['key']

    # Update content
    update_url = f"{base_url}/wiki/rest/api/content/{page_id}"
    headers = {"Content-Type": "application/json"}
    data = {
        "id": page_id,
        "type": "page",
        "title": title,
        "space": {"key": space_key},
        "version": {"number": current_version + 1},
        "body": {
            "storage": {
                "value": html_content,
                "representation": "storage"
            }
        }
    }
    response = requests.put(update_url, headers=headers, auth=auth, json=data)
    if response.status_code not in [200, 201]:
        raise Exception(f"Error updating report page: {response.text}")
    return response.json()

def lambda_handler(event, context):
    secret_name = os.environ['CONFLUENCE_SECRET_NAME']
    root_page_id = os.environ['CONFLUENCE_PAGE_ID']
    target_page_id = os.environ['TARGET_PAGE_ID']

    creds = get_confluence_credentials(secret_name)
    base_url = creds['base_url']
    auth = HTTPBasicAuth(creds['username'], creds['api_token'])

    page_data = collect_page_data(base_url, root_page_id, auth)
    html_content = generate_html_table(page_data)
    result = update_confluence_page(base_url, target_page_id, auth, html_content)

    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Analytics report updated successfully',
            'page_id': result.get('id'),
            'page_url': f"{base_url}/wiki{result.get('_links', {}).get('webui', '')}"
        })
    }
