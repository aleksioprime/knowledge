// Python в браузере: Pyodide (CPython, собранный в WebAssembly) работает в отдельном потоке,
// чтобы долгий или зависший код не блокировал страницу
const PYODIDE = 'https://cdn.jsdelivr.net/pyodide/v0.27.7/full/'

declare function importScripts(...urls: string[]): void
declare function loadPyodide(opts: object): Promise<any>

let pyodide: any = null

// Вывод без буферизации: print(..., end=' ') появляется сразу, а не после перевода строки
const stream = (emit: (s: string) => void) => {
  const decoder = new TextDecoder()
  return { write: (buf: Uint8Array) => (emit(decoder.decode(buf, { stream: true })), buf.length) }
}
const MUTE = { write: (buf: Uint8Array) => buf.length }

const RUN_WITH_LAST_EXPR = `
import sys
from pyodide.code import eval_code_async
try:
    _result = await eval_code_async(code, g, filename='<exec>')
    if _result is not None:
        print(repr(_result))
finally:
    # Строка без перевода строки (print(..., end=' ')) иначе осталась бы в буфере
    sys.stdout.flush()
    sys.stderr.flush()
`

const CANCEL_PENDING = `
import asyncio
_pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
for _t in _pending:
    _t.cancel()
await asyncio.gather(*_pending, return_exceptions=True)
`

async function init() {
  if (pyodide) return pyodide
  importScripts(PYODIDE + 'pyodide.js')
  pyodide = await loadPyodide({ indexURL: PYODIDE })
  return pyodide
}

self.onmessage = async (e: MessageEvent<{ code: string; prelude: string[] }>) => {
  const post = (type: string, text = '') => self.postMessage({ type, text })
  const { code, prelude } = e.data
  try {
    post('status', 'Загружаю Python…')
    const py = await init()
    await py.loadPackagesFromImports([...prelude, code].join('\n'))
    // Свежий словарь глобалов на каждый запуск: результат не зависит от прошлых
    const globals = py.toPy({ __name__: '__main__' })
    if (prelude.length) {
      // Предыдущие блоки цепочки выполняются молча — только чтобы определить нужные имена
      post('status', 'Выполняю предыдущие блоки…')
      py.setStdout(MUTE)
      py.setStderr(MUTE)
      for (const block of prelude) {
        try {
          await py.runPythonAsync(block, { globals })
        } catch (err: any) {
          throw new Error('Ошибка в одном из предыдущих блоков:\n' + String(err?.message ?? err))
        }
      }
      await py.runPythonAsync('import sys; sys.stdout.flush(); sys.stderr.flush()')
    }
    py.setStdout(stream((s) => post('stdout', s)))
    py.setStderr(stream((s) => post('stderr', s)))
    post('status', 'Выполняется…')
    const started = performance.now()
    try {
      // Как в Jupyter: если блок заканчивается выражением, печатаем его repr
      const runner = py.toPy({ code, g: globals })
      try {
        await py.runPythonAsync(RUN_WITH_LAST_EXPR, { globals: runner })
      } finally {
        runner.destroy()
      }
    } finally {
      // Как asyncio.run: задачи, которых никто не дождался, отменяются,
      // иначе они допечатали бы свой вывод в следующий запуск
      py.setStdout(MUTE)
      py.setStderr(MUTE)
      await py.runPythonAsync(CANCEL_PENDING)
      globals.destroy()
    }
    post('done', ((performance.now() - started) / 1000).toFixed(2))
  } catch (err: any) {
    post('error', String(err?.message ?? err))
  }
}
