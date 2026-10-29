// Python в браузере: Pyodide (CPython, собранный в WebAssembly) работает в отдельном потоке,
// чтобы долгий или зависший код не блокировал страницу
const PYODIDE = 'https://cdn.jsdelivr.net/pyodide/v0.27.7/full/'

declare function importScripts(...urls: string[]): void
declare function loadPyodide(opts: object): Promise<any>

let pyodide: any = null

async function init() {
  if (pyodide) return pyodide
  importScripts(PYODIDE + 'pyodide.js')
  pyodide = await loadPyodide({ indexURL: PYODIDE })
  return pyodide
}

self.onmessage = async (e: MessageEvent<{ code: string }>) => {
  const post = (type: string, text = '') => self.postMessage({ type, text })
  try {
    post('status', 'Загружаю Python…')
    const py = await init()
    py.setStdout({ batched: (s: string) => post('stdout', s) })
    py.setStderr({ batched: (s: string) => post('stderr', s) })
    post('status', 'Выполняется…')
    const started = performance.now()
    await py.loadPackagesFromImports(e.data.code)
    // Свежий словарь глобалов на каждый запуск: результат не зависит от прошлых
    const globals = py.toPy({})
    await py.runPythonAsync(e.data.code, { globals })
    globals.destroy()
    post('done', ((performance.now() - started) / 1000).toFixed(2))
  } catch (err: any) {
    post('error', String(err?.message ?? err))
  }
}
