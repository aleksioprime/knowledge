"""Приёмник событий Sentry для проверки без внешнего сервиса.

Принимает конверты (envelope) на /api/<project>/envelope/ и печатает главное из каждого события.
Полные события складывает в events.jsonl.
"""
import gzip
import json
import zlib
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

OUT = Path('events.jsonl')


def decode(body: bytes, encoding: str) -> bytes:
    if encoding == 'gzip':
        return gzip.decompress(body)
    if encoding == 'deflate':
        return zlib.decompress(body)
    if encoding == 'br':
        import brotli  # SDK сжимает brotli, только если пакет установлен

        return brotli.decompress(body)
    return body


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        body = self.rfile.read(int(self.headers['Content-Length']))
        body = decode(body, self.headers.get('Content-Encoding', ''))
        # Конверт: строка-заголовок, затем пары «заголовок элемента» + «данные»
        lines = body.split(b'\n')
        for item_header, payload in zip(lines[1::2], lines[2::2]):
            item_type = json.loads(item_header)['type']
            if item_type not in ('event', 'transaction'):
                continue
            event = json.loads(payload)
            with OUT.open('a') as file:
                file.write(json.dumps(event, ensure_ascii=False) + '\n')
            summary = event.get('transaction') if item_type == 'transaction' else (
                event.get('exception', {}).get('values', [{}])[-1].get('type')
                or event.get('message') or event.get('logentry', {}).get('message')
            )
            print(f'{item_type:11} {summary}', flush=True)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{}')

    def log_message(self, *args) -> None:
        pass


if __name__ == '__main__':
    HTTPServer(('127.0.0.1', 47001), Handler).serve_forever()
