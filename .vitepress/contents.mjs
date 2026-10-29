// Блок «## Содержание» в README папки — единственный источник меню сайта.
// Используется конфигом (боковое меню) и проверкой после сборки (каждая заметка упомянута в содержании)
import fs from 'node:fs'
import path from 'node:path'

// Пункты блока «## Содержание»: ссылки из списка и подзаголовки «###», под которыми они стоят.
// null — в README нет такого блока. whole: все ссылки файла (главный README, упоминания примеров)
export function readContents(readme, whole = false) {
  const text = fs.readFileSync(readme, 'utf8')
  if (whole) return [...text.matchAll(/\[([^\]]+)\]\(([^)\s]+)\)/g)].map((m) => ({ text: m[1], href: m[2], group: null }))
  const m = text.match(/^## Содержание[^\n]*\n([\s\S]*?)(?=^## |(?![\s\S]))/m)
  if (!m) return null
  const items = []
  let group = null
  for (const line of m[1].split('\n')) {
    const heading = line.match(/^###\s+(.+)/)
    if (heading) {
      group = heading[1].trim()
      continue
    }
    const link = line.match(/^(?:-|\d+\.)\s+\[(.+?)\]\(([^)\s]+)\)/)
    if (link) items.push({ text: link[1], href: link[2], group })
  }
  return items
}

// Путь, на который ведёт пункт содержания; null — не страница (файл примера, папка)
export function contentsTarget(dir, item) {
  const target = item.href.split('#')[0]
  if (!target.endsWith('.md') || /^[a-z]+:/i.test(target)) return null
  return path.resolve(dir, target)
}

const SKIP_DIRS = new Set(['node_modules', 'dist'])

// Все заметки под папкой: .md вне служебных и скрытых папок
export function walkNotes(dir) {
  const out = []
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (e.name.startsWith('.') || SKIP_DIRS.has(e.name)) continue
    const full = path.join(dir, e.name)
    if (e.isDirectory()) out.push(...walkNotes(full))
    else if (e.name.endsWith('.md')) out.push(full)
  }
  return out
}
