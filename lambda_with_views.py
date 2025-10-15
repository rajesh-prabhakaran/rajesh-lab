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
    url = f"{base_url}/wiki/rest/api/content/{page_id}?expand=version,metadata.labels,history,space"
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

def generate_html_table(page_info):
    html = "<h2>Confluence Page Analytics Report</h2>"
    html += "<table border='1' cellpadding='5' cellspacing='0'>"
    html += "<tr><th>Title</th><th>Last Updated</th><th>Version</th><th>Creator</th><th>Labels</th><th>View Count</th></tr>"
    html += f"<tr><td>{page_info['title']}</td><td>{page_info['last_updated']}</td><td>{page_info['version']}</td><td>{page_info['creator']}</td><td>{', '.join(page_info['labels'])}</td><td>{page_info['view_count']}</td></tr>"
    html += "</table>"
    return html

def post_to_confluence(base_url, target_space_key, auth, html_content):
    url = f"{base_url}/wiki/rest/api/content"
    headers = {"Content-Type": "application/json"}
    data = {
        "type": "page",
        "title": "Confluence Page Analytics Report",
        "space": {"key": target_space_key},
        "body": {
            "storage": {
                "value": html_content,
                "representation": "storage"
            }
        }
    }
    response = requests.post(url, headers=headers, auth=auth, json=data)
    if response.status_code not in [200, 201]:
        raise Exception(f"Error posting report: {response.text}")
    return response.json()

def lambda_handler(event, context):
    secret_name = os.environ['CONFLUENCE_SECRET_NAME']
    page_id = os.environ['CONFLUENCE_PAGE_ID']
    target_space_key = os.environ['TARGET_SPACE_KEY']

    creds = get_confluence_credentials(secret_name)
    base_url = creds['base_url']
    auth = HTTPBasicAuth(creds['username'], creds['api_token'])

    page = fetch_page_metadata(base_url, page_id, auth)
    view_count = fetch_view_count(base_url, page_id, auth)

    page_info = {
        'title': page.get('title'),
        'id': page_id,
        'last_updated': page.get('version', {}).get('when'),
        'version': page.get('version', {}).get('number'),
        'creator': page.get('history', {}).get('createdBy', {}).get('displayName'),
        'labels': [label['name'] for label in page.get('metadata', {}).get('labels', {}).get('results', [])],
        'view_count': view_count
    }

    html_content = generate_html_table(page_info)
    result = post_to_confluence(base_url, target_space_key, auth, html_content)

    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Analytics report posted successfully',
            'page_id': result.get('id'),
            'page_url': f"{base_url}/wiki{result.get('_links', {}).get('webui', '')}"
        })
    }
