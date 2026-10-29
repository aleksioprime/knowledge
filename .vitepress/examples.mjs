// Примеры кода: папка examples/ рядом с заметками. Если в ней лежат файлы — это один пример,
// если только подпапки — каждая подпапка отдельный пример. Каждый пример скачивается архивом
// (их собирает pack-examples.mjs после сборки) и открывается на GitHub
import fs from 'node:fs'
import path from 'node:path'

const SKIP = new Set(['node_modules', 'dist', '.pytest_cache', '__pycache__'])

// Папка с примером: { name, dir (абсолютный путь), rel (путь от docs/ через «/») }
export function exampleItems(examplesDir, docsRoot) {
  if (!fs.existsSync(examplesDir)) return []
  const entries = fs.readdirSync(examplesDir, { withFileTypes: true }).filter((e) => !e.name.startsWith('.') && !SKIP.has(e.name))
  const dirs = entries.some((e) => e.isFile()) ? [examplesDir] : entries.filter((e) => e.isDirectory()).map((e) => path.join(examplesDir, e.name))
  return dirs.map((dir) => ({
    name: dir === examplesDir ? path.basename(path.dirname(dir)) : path.basename(dir),
    dir,
    rel: path.relative(docsRoot, dir).split(path.sep).join('/'),
  }))
}

// Все папки examples/ под docs/
export function findExamplesDirs(root) {
  const out = []
  for (const e of fs.readdirSync(root, { withFileTypes: true })) {
    if (!e.isDirectory() || e.name.startsWith('.') || SKIP.has(e.name)) continue
    const full = path.join(root, e.name)
    if (e.name === 'examples') out.push(full)
    else out.push(...findExamplesDirs(full))
  }
  return out
}

// Название примера: заголовок его README, иначе имя папки
export function exampleTitle(item) {
  const readme = path.join(item.dir, 'README.md')
  if (!fs.existsSync(readme)) return item.name
  const m = fs.readFileSync(readme, 'utf8').match(/^#\s+(.+)$/m)
  return m ? m[1].replace(/`/g, '') : item.name
}
