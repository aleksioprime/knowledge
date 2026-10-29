from collections import defaultdict

history: dict[int, list[dict]] = defaultdict(list)   # источник правды: база
seq: dict[int, int] = defaultdict(int)                # счётчик внутри чата
online: dict[str, list[dict]] = {'boris': []}         # открытые соединения


def send_message(chat_id: int, author: str, text: str) -> dict:
    seq[chat_id] += 1                                 # одно место выдаёт номер
    message = {'chat_id': chat_id, 'seq': seq[chat_id], 'author': author, 'text': text}
    history[chat_id].append(message)                  # сначала сохранить
    for user in ('anna', 'boris'):                    # потом разослать
        if user != author and user in online:
            online[user].append(message)
    return message


send_message(42, 'anna', 'Привет!')
send_message(42, 'anna', 'Отчёт готов?')
print([m['seq'] for m in history[42]])      # [1, 2]
print(online['boris'][-1]['text'])          # Отчёт готов?
print([m['text'] for m in history[42] if m['seq'] > 1])  # ['Отчёт готов?'] — дочитать после seq 1
