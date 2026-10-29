// Архивы примеров для скачивания с сайта: каждый пример → .vitepress/dist/<путь>.zip.
// В архив попадают только файлы из git (без node_modules, кэшей, .env и собранных артефактов).
// Запуск после `vitepress build`: node .vitepress/pack-examples.mjs
import { execFileSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import { exampleItems, findExamplesDirs } from './examples.mjs'

const ROOT = path.resolve(import.meta.dirname, '..')
const DOCS = path.join(ROOT, 'docs')
const DIST = path.join(ROOT, '.vitepress/dist')

if (!fs.existsSync(path.join(DIST, 'index.html'))) {
  console.error('Сайт не собран: сначала выполните vitepress build')
  process.exit(1)
}

let count = 0
for (const examplesDir of findExamplesDirs(DOCS)) {
  for (const item of exampleItems(examplesDir, DOCS)) {
    const parent = path.dirname(item.dir)
    const files = execFileSync('git', ['ls-files', path.basename(item.dir)], { cwd: parent, encoding: 'utf8' })
    if (!files.trim()) continue
    const out = path.join(DIST, item.rel + '.zip')
    fs.mkdirSync(path.dirname(out), { recursive: true })
    fs.rmSync(out, { force: true })
    execFileSync('zip', ['-q', '-X', out, '-@'], { cwd: parent, input: files })
    count++
  }
}
console.log(`Архивов примеров: ${count}`)
