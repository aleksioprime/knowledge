// Один поток на язык и страницу: Pyodide (~10 МБ) и PGlite (~4 МБ) грузятся один раз,
// дальше запуски быстрые
export type Lang = 'python' | 'sql'
export type Message =
  | { type: 'status' | 'stdout' | 'stderr' | 'done' | 'error'; text: string }
  | { type: 'table'; fields: string[]; rows: unknown[][] }

const workers: Partial<Record<Lang, Worker>> = {}
const current: Partial<Record<Lang, (m: Message) => void>> = {}

function getWorker(lang: Lang) {
  if (!workers[lang]) {
    const worker =
      lang === 'python'
        ? new Worker(new URL('./python-worker.ts', import.meta.url))
        : new Worker(new URL('./sql-worker.ts', import.meta.url), { type: 'module' })
    worker.onmessage = (e: MessageEvent<Message>) => current[lang]?.(e.data)
    workers[lang] = worker
  }
  return workers[lang]!
}

export function runCode(lang: Lang, code: string, onMessage: (m: Message) => void, prelude: string[] = []) {
  // Предыдущий запуск ещё идёт — прерываем его вместе с потоком
  if (current[lang]) stopCode(lang)
  current[lang] = (m) => {
    onMessage(m)
    if (m.type === 'done' || m.type === 'error') delete current[lang]
  }
  getWorker(lang).postMessage({ code, prelude })
}

export function stopCode(lang: Lang) {
  workers[lang]?.terminate()
  delete workers[lang]
  current[lang]?.({ type: 'error', text: 'Остановлено' })
  delete current[lang]
}
