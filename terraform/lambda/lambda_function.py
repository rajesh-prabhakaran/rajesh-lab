import json
import boto3
import os
import requests
from requests.auth import HTTPBasicAuth

def get_confluence_credentials(secret_name):
    """Fetch Confluence credentials from AWS Secrets Manager"""
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    secret = json.loads(response['SecretString'])
    return secret['base_url'], secret['username'], secret['api_token']

def fetch_confluence_pages(base_url, space_key, auth, headers):
    """Fetch pages from Confluence space with pagination and analytics"""
    page_data = []
    start = 0
    limit = 50

    while True:
        url = f"{base_url}/wiki/rest/api/content?spaceKey={space_key}&limit={limit}&start={start}&expand=version,history,metadata.labels"
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
                'created_date': page.get('history', {}).get('createdDate'),
                'labels': [label['name'] for label in page.get('metadata', {}).get('labels', {}).get('results', [])]
            }

            # Try to fetch view count if analytics API is available
            analytics_url = f"{base_url}/wiki/rest/analytics/1.0/content/{page_info['id']}/report/views"
            analytics_response = requests.get(analytics_url, headers=headers, auth=auth)
            if analytics_response.status_code == 200:
                analytics_data = analytics_response.json()
                page_info['view_count'] = analytics_data.get('views', {}).get('count')
            else:
                page_info['view_count'] = 'N/A'

            page_data.append(page_info)

        if not data.get('_links', {}).get('next'):
            break
        start += limit

    return page_data

def lambda_handler(event, context):
    """Main Lambda handler"""
    secret_name = os.environ.get('CONFLUENCE_SECRET_NAME')
    space_key = event.get('space_key', 'YOUR_SPACE_KEY')

    try:
        base_url, username, api_token = get_confluence_credentials(secret_name)
        headers = { "Accept": "application/json" }
        auth = HTTPBasicAuth(username, api_token)

        page_data = fetch_confluence_pages(base_url, space_key, auth, headers)

        return {
            'statusCode': 200,
            'body': json.dumps(page_data)
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': str(e)
        }
