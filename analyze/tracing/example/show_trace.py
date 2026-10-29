"""Дерево спанов последних трасс из Jaeger: python show_trace.py tasks --last 2 --min-ms 300"""
import argparse
import json
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode
from urllib.request import urlopen

JAEGER = 'http://localhost:56686'


def fetch_spans(service: str, min_ms: int) -> list[dict]:
    now = datetime.now(UTC)
    params = urlencode({
        'query.service_name': service,
        'query.start_time_min': (now - timedelta(hours=1)).isoformat(),
        'query.start_time_max': now.isoformat(),
        'query.search_depth': 1000,
        'query.duration_min': f'{min_ms}ms',
    })
    with urlopen(f'{JAEGER}/api/v3/traces?{params}') as response:
        data = json.load(response)
    spans = []
    for resource in data['result']['resourceSpans']:
        attrs = {a['key']: a['value'] for a in resource['resource']['attributes']}
        service_name = attrs['service.name']['stringValue']
        for scope in resource['scopeSpans']:
            for span in scope['spans']:
                spans.append({**span, 'service': service_name})
    return spans


def print_tree(spans: list[dict]) -> None:
    by_parent: dict[str, list[dict]] = {}
    for span in spans:
        by_parent.setdefault(span.get('parentSpanId', ''), []).append(span)
    root = by_parent[''][0]
    start = int(root['startTimeUnixNano'])

    def show(span: dict, depth: int) -> None:
        offset = (int(span['startTimeUnixNano']) - start) / 1e6
        duration = (int(span['endTimeUnixNano']) - int(span['startTimeUnixNano'])) / 1e6
        status = 'ERROR' if span['status'].get('code') == 2 else ''
        name = '  ' * depth + f"{span['service']}: {span['name']}"
        print(f'{name:<40} +{offset:5.1f} мс {duration:6.1f} мс {status}')
        for child in sorted(by_parent.get(span['spanId'], []), key=lambda s: int(s['startTimeUnixNano'])):
            show(child, depth + 1)

    print('trace_id', root['traceId'])
    show(root, 0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('service')
    parser.add_argument('--last', type=int, default=1)
    parser.add_argument('--min-ms', type=int, default=0)
    args = parser.parse_args()
    traces: dict[str, list[dict]] = {}
    for span in fetch_spans(args.service, args.min_ms):
        traces.setdefault(span['traceId'], []).append(span)
    print('трасс за последний час:', len(traces))
    latest = sorted(traces.values(), key=lambda s: min(int(x['startTimeUnixNano']) for x in s))[-args.last:]
    for spans in latest:
        print_tree(spans)
        print()
