"""Последние логи стенда из Elasticsearch: python show_logs.py [request_id]."""
import json
import sys
from urllib.request import Request, urlopen

ES = 'http://localhost:49200'

query = {'match_all': {}}
if len(sys.argv) > 1:
    query = {'term': {'request_id': sys.argv[1]}}

body = {
    'size': 30,
    'sort': [{'@timestamp': 'desc'}],
    'query': query,
    '_source': ['service.name', 'level', 'status', 'method', 'uri', 'request_id', 'message', 'task_id'],
}
request = Request(f'{ES}/filebeat-*/_search', data=json.dumps(body).encode(),
                  headers={'Content-Type': 'application/json'})
hits = json.load(urlopen(request))['hits']['hits']

for hit in reversed(hits):  # последние 30, по порядку времени
    doc = hit['_source']
    service = doc.get('service', {}).get('name', '?')
    if 'status' in doc:
        text = f"{doc['method']} {doc['uri']} → {doc['status']}"
    else:
        text = f"{doc.get('level', '-'):7} {doc.get('message', '')}"
    print(f"{service:6} {str(doc.get('request_id'))[:8]:8}  {text}")
