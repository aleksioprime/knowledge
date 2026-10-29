// PostgreSQL в браузере: PGlite — настоящий Postgres, собранный в WebAssembly.
// Каждый запуск получает чистую базу в памяти, поэтому примеры не мешают друг другу
const PGLITE = 'https://cdn.jsdelivr.net/npm/@electric-sql/pglite@0.5.8/dist/index.js'

let PGlite: any = null

// Делит текст на запросы по «;», не заглядывая в строки, идентификаторы в кавычках,
// $$-тела функций и комментарии
export function splitStatements(sql: string): string[] {
  const out: string[] = []
  let start = 0
  let i = 0
  while (i < sql.length) {
    const ch = sql[i]
    const rest = sql.slice(i)
    if (rest.startsWith('--')) {
      const end = sql.indexOf('\n', i)
      i = end < 0 ? sql.length : end
    } else if (rest.startsWith('/*')) {
      const end = sql.indexOf('*/', i + 2)
      i = end < 0 ? sql.length : end + 2
    } else if (ch === "'" || ch === '"') {
      let j = i + 1
      while (j < sql.length && !(sql[j] === ch && sql[j + 1] !== ch)) j += sql[j] === ch ? 2 : 1
      i = j + 1
    } else if (ch === '$') {
      const tag = rest.match(/^\$[A-Za-z_]*\$/)?.[0]
      if (tag) {
        const end = sql.indexOf(tag, i + tag.length)
        i = end < 0 ? sql.length : end + tag.length
      } else i++
    } else if (ch === ';') {
      out.push(sql.slice(start, i + 1))
      start = i + 1
      i++
    } else i++
  }
  out.push(sql.slice(start))
  // Остаток из одних комментариев и пробелов запросом не считается
  return out.filter((s) => s.replace(/--[^\n]*|\/\*[\s\S]*?\*\//g, '').trim())
}

// Метка результата, как её печатает psql: CREATE TABLE, INSERT 0 2, UPDATE 1
function commandTag(statement: string, affected: number) {
  const words = statement.replace(/--[^\n]*|\/\*[\s\S]*?\*\//g, ' ').trim().split(/\s+/).map((w) => w.toUpperCase())
  const [first] = words
  if (first === 'INSERT') return `INSERT 0 ${affected}`
  if (['UPDATE', 'DELETE', 'MERGE', 'COPY'].includes(first)) return `${first} ${affected}`
  if (['CREATE', 'DROP', 'ALTER'].includes(first)) {
    const object = words.slice(1).find((w) => !['OR', 'REPLACE', 'UNIQUE', 'TEMP', 'TEMPORARY', 'MATERIALIZED', 'IF', 'NOT', 'EXISTS'].includes(w))
    return `${first} ${object?.replace(/[^A-Z]/g, '') ?? ''}`.trim()
  }
  return first.replace(/;$/, '')
}

self.onmessage = async (e: MessageEvent<{ code: string; prelude: string[] }>) => {
  const post = (m: object) => self.postMessage(m)
  const { code, prelude } = e.data
  let db: any = null
  try {
    post({ type: 'status', text: 'Загружаю PostgreSQL…' })
    PGlite ??= (await import(/* @vite-ignore */ PGLITE)).PGlite
    db = new PGlite()
    await db.waitReady
    if (prelude.length) {
      // Предыдущие блоки цепочки создают таблицы и данные; их вывод не нужен
      post({ type: 'status', text: 'Выполняю предыдущие блоки…' })
      for (const block of prelude) {
        try {
          await db.exec(block)
        } catch (err: any) {
          throw new Error('Ошибка в одном из предыдущих блоков:\n' + String(err?.message ?? err))
        }
      }
    }
    post({ type: 'status', text: 'Выполняется…' })
    const started = performance.now()
    const onNotice = (n: any) => post({ type: 'stdout', text: `${n.severity ?? 'NOTICE'}: ${n.message}\n` })
    // Запросы выполняются по одному, как в psql: результаты до ошибки остаются видны
    for (const statement of splitStatements(code)) {
      const [r] = await db.exec(statement, { onNotice })
      if (r?.fields.length === 1 && r.fields[0].name === 'QUERY PLAN') {
        // План запроса читается как текст с отступами, а не как таблица
        post({ type: 'stdout', text: r.rows.map((row: any) => row['QUERY PLAN']).join('\n') + '\n' })
      } else if (r?.fields.length) {
        const names = r.fields.map((f: any) => f.name)
        post({ type: 'table', fields: names, rows: r.rows.map((row: any) => names.map((n: string) => row[n])) })
      } else {
        post({ type: 'stdout', text: commandTag(statement, r?.affectedRows ?? 0) + '\n' })
      }
    }
    post({ type: 'done', text: ((performance.now() - started) / 1000).toFixed(2) })
  } catch (err: any) {
    const detail = [err?.message ?? String(err), err?.detail && `DETAIL: ${err.detail}`, err?.hint && `HINT: ${err.hint}`]
    post({ type: 'error', text: 'ERROR: ' + detail.filter(Boolean).join('\n') })
  } finally {
    await db?.close().catch(() => {})
  }
}
