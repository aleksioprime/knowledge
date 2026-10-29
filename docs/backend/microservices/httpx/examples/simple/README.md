# HTTPX: простые примеры

Учебный сервер `server.py` отвечает быстро, медленно или с ошибками, а скрипты рядом показывают, как с ним работать через HTTPX. Объяснения — в заметке [HTTPX: основы](../../basics.md).

```bash
pip install -r requirements.txt
uvicorn server:app --port 8001
```

В другом терминале:

```bash
python basics.py        # GET и POST, параметры, JSON, raise_for_status
python timeouts.py      # таймаут чтения и ошибка соединения
python async_client.py  # 5 запросов по очереди (2.6 с) и параллельно (0.5 с)
python retries.py       # встроенные повторы транспорта и свои повторы при 503
```
