// Проверка ссылок по собранному сайту (после `vitepress build`):
// - внутренние ссылки ведут на существующую страницу, а якорь — на существующий заголовок;
// - ссылки на файлы репозитория (github.com/.../blob/main/...) указывают на файл, который есть в репозитории.
// Запуск: node .vitepress/check-links.mjs   (BASE — тот же, что при сборке, по умолчанию /)
import fs from 'node:fs'
import path from 'node:path'

const ROOT = path.resolve(import.meta.dirname, '..')
const DIST = path.join(ROOT, '.vitepress/dist')
const BASE = process.env.BASE ?? '/'
const REPO_BLOB = 'https://github.com/aleksioprime/knowledge/blob/main/'

if (!fs.existsSync(path.join(DIST, 'index.html'))) {
  console.error('Сайт не собран: сначала выполните npm run build')
  process.exit(1)
}

const pages = new Map() // путь страницы → { html, ids }
for (const file of fs.readdirSync(DIST, { recursive: true })) {
  if (!file.endsWith('.html') || file === '404.html') continue
  const html = fs.readFileSync(path.join(DIST, file), 'utf8')
  const ids = new Set([...html.matchAll(/\sid="([^"]+)"/g)].map((m) => decodeEntities(m[1])))
  pages.set('/' + file.split(path.sep).join('/'), { html, ids })
}

function decodeEntities(s) {
  return s.replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>')
}

// /python/ → /python/index.html, /python/oop/oop → /python/oop/oop.html
function resolvePage(urlPath) {
  const p = decodeURIComponent(urlPath)
  const candidates = p.endsWith('/') ? [p + 'index.html'] : [p + '.html', p, p + '/index.html']
  return candidates.find((c) => pages.has(c))
}

const problems = []
for (const [page, { html, ids }] of pages) {
  // Ссылки внутри содержимого страницы; навигацию и подвал темы проверяет сам VitePress
  const content = html.match(/<main[\s\S]*?<\/main>/)?.[0] ?? ''
  for (const [, rawHref] of content.matchAll(/<a\s[^>]*?href="([^"]+)"/g)) {
    const href = decodeEntities(rawHref)
    if (href.startsWith(REPO_BLOB)) {
      const file = decodeURIComponent(href.slice(REPO_BLOB.length).split('#')[0])
      if (!fs.existsSync(path.join(ROOT, file))) problems.push([page, href, 'нет файла в репозитории'])
      continue
    }
    if (/^[a-z]+:/i.test(href) || href.startsWith('//')) continue
    if (/\/\//.test(href)) {
      problems.push([page, href, 'двойная косая черта'])
      continue
    }
    const [target, anchor] = href.split('#')
    let targetPage = page
    if (target) {
      let sitePath
      if (target.startsWith('/')) {
        if (!target.startsWith(BASE)) {
          problems.push([page, href, 'ссылка мимо сайта'])
          continue
        }
        sitePath = '/' + target.slice(BASE.length)
      } else {
        // Относительная ссылка считается от адреса страницы: /a/index.html → /a/, /a/b.html → /a/
        const url = page.endsWith('/index.html') ? page.slice(0, -'index.html'.length) : page.replace(/\.html$/, '')
        const dir = url.endsWith('/') ? url : path.posix.dirname(url) + '/'
        sitePath = path.posix.normalize(dir + target) + (target.endsWith('/') ? '/' : '')
      }
      targetPage = resolvePage(sitePath)
      if (!targetPage) {
        // Ассеты (картинки, файлы из public) лежат в dist как есть
        if (fs.existsSync(path.join(DIST, decodeURIComponent(sitePath)))) continue
        problems.push([page, href, 'нет страницы'])
        continue
      }
    }
    if (anchor && !pages.get(targetPage).ids.has(decodeURIComponent(anchor))) {
      problems.push([page, href, 'нет якоря'])
    }
  }
}

for (const [page, href, why] of problems) console.log(`${page}\t${href}\t${why}`)
console.log(`\nСтраниц: ${pages.size}, битых ссылок: ${problems.length}`)
process.exit(problems.length ? 1 : 0)
