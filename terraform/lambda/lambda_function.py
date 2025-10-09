import json
import os
import requests
from requests.auth import HTTPBasicAuth

def lambda_handler(event, context):
    # Environment variables or secrets manager
    base_url = os.environ['CONFLUENCE_BASE_URL']
    space_key = event.get('space_key', 'YOUR_SPACE_KEY')
    username = os.environ['CONFLUENCE_USERNAME']
    api_token = os.environ['CONFLUENCE_API_TOKEN']

    headers = {
        "Accept": "application/json"
    }

    auth = HTTPBasicAuth(username, api_token)

    page_data = []
    start = 0
    limit = 50

    while True:
        url = f"{base_url}/wiki/rest/api/content?spaceKey={space_key}&limit={limit}&start={start}&expand=version"
        response = requests.get(url, headers=headers, auth=auth)

        if response.status_code != 200:
            return {
                'statusCode': response.status_code,
                'body': f"Error fetching data: {response.text}"
            }

        data = response.json()
        results = data.get('results', [])

        for page in results:
            page_info = {
                'title': page.get('title'),
                'id': page.get('id'),
                'last_updated': page.get('version', {}).get('when'),
                'version': page.get('version', {}).get('number')
            }
            page_data.append(page_info)

        if not data.get('_links', {}).get('next'):
            break
        start += limit

    return {
        'statusCode': 200,
        'body': json.dumps(page_data)
    }
