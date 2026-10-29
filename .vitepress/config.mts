import fs from 'node:fs'
import path from 'node:path'
import { defineConfig, type DefaultTheme } from 'vitepress'
import { readContents, contentsTarget } from './contents.mjs'

const ROOT = path.resolve(__dirname, '..')
const DOCS = path.join(ROOT, 'docs') // база знаний; в корне репозитория только служебные файлы
const REPO = 'https://github.com/aleksioprime/knowledge'

// Разделы берутся из главного README: группы — заголовки «## Группа»,
// разделы — строки «- [Название](группа/раздел/README.md) — описание» под ними
function readSections() {
  const readme = fs.readFileSync(path.join(DOCS, 'README.md'), 'utf8')
  const sections: { text: string; dir: string; group: string }[] = []
  let group = 'Разделы'
  for (const line of readme.split('\n')) {
    const heading = line.match(/^##\s+(.+)/)
    if (heading) group = heading[1].trim()
    const m = line.match(/^- \[(.+?)\]\(([\w-]+(?:\/[\w-]+)*)\/README\.md\)/)
    if (m) sections.push({ text: m[1], dir: m[2], group })
  }
  return sections
}

// Меню: группа из нескольких разделов — выпадающий список, из одного — простая ссылка
function buildNav(sections: ReturnType<typeof readSections>): DefaultTheme.NavItem[] {
  const groups = new Map<string, typeof sections>()
  for (const s of sections) groups.set(s.group, [...(groups.get(s.group) ?? []), s])
  return [...groups].map(([text, items]) =>
    items.length === 1
      ? { text, link: `/${items[0].dir}/`, activeMatch: `^/${items[0].dir}/` }
      : {
          text,
          items: items.map((s) => ({ text: s.text, link: `/${s.dir}/`, activeMatch: `^/${s.dir}/` })),
          activeMatch: `^/(${items.map((s) => s.dir).join('|')})/`,
        },
  )
}

function toLink(file: string) {
  const rel = path.relative(DOCS, file).split(path.sep).join('/')
  return '/' + rel.replace(/(^|\/)README\.md$/, '$1').replace(/\.md$/, '')
}

// Боковое меню повторяет блок «## Содержание» README папки: тот же порядок, те же названия,
// подзаголовки «###» становятся группами, ссылка на README вложенной папки — вложенным меню
function contentsTree(dir: string): DefaultTheme.SidebarItem[] {
  const readme = path.join(dir, 'README.md')
  if (!fs.existsSync(readme)) return []
  const groups = new Map<string | null, DefaultTheme.SidebarItem[]>()
  for (const entry of readContents(readme) ?? []) {
    const file = contentsTarget(dir, entry)
    if (!file || !fs.existsSync(file)) continue
    const item: DefaultTheme.SidebarItem = { text: entry.text, link: toLink(file) }
    if (path.basename(file) === 'README.md') {
      const children = contentsTree(path.dirname(file))
      if (children.length) Object.assign(item, { items: children, collapsed: true })
    }
    groups.set(entry.group, [...(groups.get(entry.group) ?? []), item])
  }
  return [...groups].flatMap(([group, items]) => (group ? [{ text: group, items }] : items))
}

const HTML_TAGS = new Set([
  'a', 'b', 'i', 'em', 'strong', 'br', 'hr', 'p', 'div', 'span', 'img', 'kbd', 'sub', 'sup', 'code', 'pre',
  'details', 'summary', 'ul', 'ol', 'li', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'h1', 'h2', 'h3', 'h4',
  'blockquote', 'center', 'small', 'mark', 'figure', 'figcaption', 'picture', 'source', 'video',
])
const COMPONENTS = new Set(['RunCode', 'EventLoopDemo'])

function isAllowedHtml(html: string) {
  if (/^\s*<!--/.test(html)) return true
  const tags = [...html.matchAll(/<\/?([A-Za-z][\w-]*)/g)].map((m) => m[1])
  return tags.length > 0 && tags.every((t) => HTML_TAGS.has(t.toLowerCase()) || COMPONENTS.has(t))
}

// Алгоритм github-slugger: нижний регистр, убрать всё, кроме букв, цифр, «_», «-» и пробелов, пробелы → «-»
function githubSlug(text: string) {
  return text.trim().toLowerCase().replace(/[^\p{L}\p{M}\p{N}\p{Pc} -]/gu, '').replace(/ /g, '-')
}

function isDir(p: string) {
  return fs.existsSync(p) && fs.statSync(p).isDirectory()
}

const sections = readSections()
const sidebar: DefaultTheme.Sidebar = {}
for (const s of sections) {
  sidebar[`/${s.dir}/`] = [{ text: s.text, link: `/${s.dir}/`, items: contentsTree(path.join(DOCS, s.dir)) }]
}

export default defineConfig({
  lang: 'ru-RU',
  title: 'База знаний',
  description: 'Конспекты и примеры кода',
  base: process.env.BASE ?? '/',
  srcDir: 'docs',
  cleanUrls: true,
  lastUpdated: true,
  srcExclude: ['**/node_modules/**', '**/dist/**'],
  // README.md в каждой папке становится её индексной страницей
  rewrites: (id) => id.replace(/(^|\/)README\.md$/, '$1index.md'),
  // Битая ссылка на заметку роняет сборку; ссылки на localhost из инструкций по запуску — не битые.
  // Якоря, ссылки на файлы репозитория и полноту содержаний после сборки проверяет .vitepress/check-links.mjs
  ignoreDeadLinks: 'localhostLinks',
  markdown: {
    theme: { light: 'github-light', dark: 'github-dark' },
    // Якоря заголовков как на GitHub: ссылки вида #3-ограничение-частоты работают и в репозитории, и на сайте
    anchor: { slugify: githubSlug },
    config(md) {
      // Заметки пишутся для GitHub: «<username>» в тексте — это плейсхолдер, а не тег.
      // Пропускаем только безопасный HTML и компоненты сайта, остальное показываем как текст
      md.core.ruler.push('escape_unknown_html', (state) => {
        const escape = (token: any) => {
          token.type = token.type === 'html_block' ? 'paragraph_text' : 'text'
        }
        const walk = (tokens: any[]) => {
          for (const t of tokens) {
            if ((t.type === 'html_inline' || t.type === 'html_block') && !isAllowedHtml(t.content)) escape(t)
            if (t.children) walk(t.children)
          }
        }
        walk(state.tokens)
      })
      md.renderer.rules.paragraph_text = (tokens, idx) => `<p>${md.utils.escapeHtml(tokens[idx].content)}</p>\n`

      // «{{ ... }}» в тексте (Jinja, Grafana, Vue) Vue принял бы за интерполяцию
      const noMustache = (s: string) => s.replace(/\{\{/g, '&#123;&#123;').replace(/\}\}/g, '&#125;&#125;')
      for (const rule of ['text', 'code_inline', 'paragraph_text'] as const) {
        const orig = md.renderer.rules[rule]!
        md.renderer.rules[rule] = (...args) => noMustache(orig(...args))
      }

      const defaultFence = md.renderer.rules.fence!
      md.renderer.rules.fence = (tokens, idx, options, env, self) => {
        const token = tokens[idx]
        // ```python run / ```sql run — блок с кнопкой «Запустить». Связи между блоками одного языка:
        // session=имя — перед запуском выполняются все блоки выше из этой цепочки;
        // setup=имя — подготовка (например, таблицы с данными), uses=имя — перед запуском выполняется только она
        const m = token.info.match(/^(python|sql)\s+run\b(.*)$/)
        if (!m) return defaultFence(tokens, idx, options, env, self)
        token.info = m[1]
        const html = defaultFence(tokens, idx, options, env, self)
        const attrs = [...m[2].matchAll(/\b(session|setup|uses)=([\w-]+)/g)].map(([, k, v]) => ` ${k}="${v}"`).join('')
        return `<RunCode lang="${m[1]}" code="${encodeURIComponent(token.content)}"${attrs}>${html}</RunCode>`
      }

      const defaultRender = md.renderer.rules.link_open
        ?? ((tokens, idx, options, _env, self) => self.renderToken(tokens, idx, options))
      md.renderer.rules.link_open = (tokens, idx, options, env, self) => {
        const href = tokens[idx].attrGet('href')
        const dir = path.posix.dirname(env.relativePath ?? '')
        const readme = href?.match(/^([^:#]*?)(?:^|\/)README\.md(#.*)?$/)
        if (href && readme && !/^[a-z]+:|^\//i.test(href)) {
          // README.md папки стал её index-страницей: ссылка ведёт на папку, а не на /README
          const target = path.posix.normalize(path.posix.join(dir, readme[1] || '.'))
          tokens[idx].attrSet('href', (target === '.' ? '/' : `/${target}/`) + (readme[2] ?? ''))
        } else if (href && !/^[a-z]+:|^#|^\//i.test(href) && isDir(path.join(DOCS, dir, href.split('#')[0]))) {
          // Ссылка на папку: с README — её страница на сайте, без README (примеры кода) — папка на GitHub
          const target = path.posix.normalize(path.posix.join(dir, href.split('#')[0])).replace(/\/$/, '')
          if (fs.existsSync(path.join(DOCS, target, 'README.md'))) {
            tokens[idx].attrSet('href', `/${target}/` + (href.includes('#') ? '#' + href.split('#')[1] : ''))
          } else {
            tokens[idx].attrSet('href', `${REPO}/tree/main/docs/${target}`)
            tokens[idx].attrSet('target', '_blank')
          }
        } else if (href && !/^[a-z]+:|^#|^\//i.test(href) && !/\.md(#|$)/.test(href) && /\.\w+(#|$)/.test(href)) {
          tokens[idx].attrSet('href', `${REPO}/blob/main/docs/${path.posix.normalize(path.posix.join(dir, href))}`)
          tokens[idx].attrSet('target', '_blank')
        }
        return defaultRender(tokens, idx, options, env, self)
      }
    },
  },
  themeConfig: {
    nav: buildNav(sections),
    sidebar,
    outline: { level: [2, 3], label: 'На странице' },
    search: {
      provider: 'local',
      options: {
        translations: {
          button: { buttonText: 'Поиск', buttonAriaLabel: 'Поиск' },
          modal: { noResultsText: 'Ничего не найдено', resetButtonTitle: 'Сбросить', footer: { selectText: 'выбрать', navigateText: 'перейти', closeText: 'закрыть' } },
        },
      },
    },
    socialLinks: [{ icon: 'github', link: REPO }],
    editLink: { pattern: `${REPO}/edit/main/docs/:path`, text: 'Редактировать на GitHub' },
    docFooter: { prev: 'Назад', next: 'Дальше' },
    lastUpdated: { text: 'Обновлено' },
    darkModeSwitchLabel: 'Тема',
    sidebarMenuLabel: 'Меню',
    returnToTopLabel: 'Наверх',
  },
})
