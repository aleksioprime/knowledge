// Один поток с Python на страницу: Pyodide грузится один раз (~10 МБ), дальше запуски мгновенные
type Message = { type: 'status' | 'stdout' | 'stderr' | 'done' | 'error'; text: string }

let worker: Worker | null = null
let current: ((m: Message) => void) | null = null

function getWorker() {
  if (!worker) {
    worker = new Worker(new URL('./python-worker.ts', import.meta.url))
    worker.onmessage = (e: MessageEvent<Message>) => current?.(e.data)
  }
  return worker
}

export function runPython(code: string, onMessage: (m: Message) => void) {
  // Предыдущий запуск ещё идёт — прерываем его вместе с потоком
  if (current) stopPython()
  current = (m) => {
    onMessage(m)
    if (m.type === 'done' || m.type === 'error') current = null
  }
  getWorker().postMessage({ code })
}

export function stopPython() {
  worker?.terminate()
  worker = null
  current?.({ type: 'error', text: 'Остановлено' })
  current = null
}
