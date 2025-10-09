import json
import os
import requests
from requests.auth import HTTPBasicAuth
import boto3

def get_confluence_credentials(secret_name):
    client = boto3.client('secretsmanager')
    secret = client.get_secret_value(SecretId=secret_name)
    return json.loads(secret['SecretString'])

def fetch_confluence_pages(base_url, space_key, auth):
    headers = {"Accept": "application/json"}
    page_data = []
    start = 0
    limit = 50

    while True:
        url = f"{base_url}/wiki/rest/api/content?spaceKey={space_key}&limit={limit}&start={start}&expand=version,metadata.labels,history"
        response = requests.get(url, headers=headers, auth=auth)
        if response.status_code != 200:
            raise Exception(f"Error fetching data: {response.text}")

        data = response.json()
        results = data.get('results', [])

        for page in results:
            page_info = {
                'title': page.get('title'),
                'id': page.get('id'),
                'last_updated': page.get('version', {}).get('when'),
                'version': page.get('version', {}).get('number'),
                'creator': page.get('history', {}).get('createdBy', {}).get('displayName'),
                'labels': [label['name'] for label in page.get('metadata', {}).get('labels', {}).get('results', [])],
                'view_count': page.get('metadata', {}).get('view', {}).get('count', 'N/A')  # May not be available
            }
            page_data.append(page_info)

        if not data.get('_links', {}).get('next'):
            break
        start += limit

    return page_data

def generate_html_table(page_data):
    html = "<h2>Confluence Page Analytics Report</h2>"
    html += "<table border='1' cellpadding='5' cellspacing='0'>"
    html += "<tr><th>Title</th><th>Last Updated</th><th>Version</th><th>Creator</th><th>Labels</th><th>View Count</th></tr>"
    for page in page_data:
        html += f"<tr><td>{page['title']}</td><td>{page['last_updated']}</td><td>{page['version']}</td><td>{page['creator']}</td><td>{', '.join(page['labels'])}</td><td>{page['view_count']}</td></tr>"
    html += "</table>"
    return html

def post_to_confluence(base_url, space_key, auth, html_content):
    url = f"{base_url}/wiki/rest/api/content"
    headers = {
        "Content-Type": "application/json"
    }

    data = {
        "type": "page",
        "title": "Confluence Page Analytics Report",
        "space": {"key": space_key},
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
    space_key = os.environ.get("CONFLUENCE_SPACE_KEY", "DEFAULT_SPACE_KEY")

    creds = get_confluence_credentials(secret_name)
    base_url = creds['base_url']
    auth = HTTPBasicAuth(creds['username'], creds['api_token'])

    page_data = fetch_confluence_pages(base_url, space_key, auth)
    html_content = generate_html_table(page_data)
    result = post_to_confluence(base_url, space_key, auth, html_content)

    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Analytics report posted successfully',
            'page_id': result.get('id'),
            'page_url': f"{base_url}/wiki{result.get('_links', {}).get('webui', '')}"
        })
    }
