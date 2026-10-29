import fs from 'node:fs'
import path from 'node:path'
import { defineConfig, type DefaultTheme } from 'vitepress'

const ROOT = path.resolve(__dirname, '..')
const REPO = 'https://github.com/aleksioprime/knowledge'
const EXCLUDE = ['node_modules', '.git', '.vitepress', '.claude', '.github', '.vscode']

// Разделы берутся из главного README: «- [Название](папка/README.md) — описание»
function readSections() {
  const readme = fs.readFileSync(path.join(ROOT, 'README.md'), 'utf8')
  const sections: { text: string; dir: string }[] = []
  for (const m of readme.matchAll(/^- \[(.+?)\]\(([\w-]+)\/README\.md\)/gm)) {
    sections.push({ text: m[1], dir: m[2] })
  }
  return sections
}

function titleOf(file: string) {
  const text = fs.readFileSync(file, 'utf8')
  const m = text.match(/^#\s+(.+)$/m)
  return m ? m[1].replace(/`/g, '') : path.basename(file, '.md')
}

function toLink(file: string) {
  const rel = path.relative(ROOT, file).split(path.sep).join('/')
  return '/' + rel.replace(/(^|\/)README\.md$/, '$1').replace(/\.md$/, '')
}

// Дерево сайдбара повторяет дерево папок: README папки — её страница, остальные .md — пункты
function buildTree(dir: string): DefaultTheme.SidebarItem[] {
  const items: DefaultTheme.SidebarItem[] = []
  const entries = fs.readdirSync(dir, { withFileTypes: true })
    .filter((e) => !e.name.startsWith('.') && !EXCLUDE.includes(e.name))
    .sort((a, b) => a.name.localeCompare(b.name))

  for (const e of entries) {
    const full = path.join(dir, e.name)
    if (e.isFile() && e.name.endsWith('.md') && e.name !== 'README.md') {
      items.push({ text: titleOf(full), link: toLink(full) })
    } else if (e.isDirectory()) {
      const children = buildTree(full)
      const readme = path.join(full, 'README.md')
      const hasReadme = fs.existsSync(readme)
      if (!hasReadme && children.length === 0) continue
      items.push({
        text: hasReadme ? titleOf(readme) : e.name,
        link: hasReadme ? toLink(readme) : undefined,
        items: children.length ? children : undefined,
        collapsed: children.length ? true : undefined,
      })
    }
  }
  return items
}

const HTML_TAGS = new Set([
  'a', 'b', 'i', 'em', 'strong', 'br', 'hr', 'p', 'div', 'span', 'img', 'kbd', 'sub', 'sup', 'code', 'pre',
  'details', 'summary', 'ul', 'ol', 'li', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'h1', 'h2', 'h3', 'h4',
  'blockquote', 'center', 'small', 'mark', 'figure', 'figcaption', 'picture', 'source', 'video',
])
const COMPONENTS = new Set(['RunPython', 'EventLoopDemo'])

function isAllowedHtml(html: string) {
  if (/^\s*<!--/.test(html)) return true
  const tags = [...html.matchAll(/<\/?([A-Za-z][\w-]*)/g)].map((m) => m[1])
  return tags.length > 0 && tags.every((t) => HTML_TAGS.has(t.toLowerCase()) || COMPONENTS.has(t))
}

const sections = readSections()
const sidebar: DefaultTheme.Sidebar = {}
for (const s of sections) {
  sidebar[`/${s.dir}/`] = [{ text: s.text, link: `/${s.dir}/`, items: buildTree(path.join(ROOT, s.dir)) }]
}

export default defineConfig({
  lang: 'ru-RU',
  title: 'База знаний',
  description: 'Конспекты и примеры кода',
  base: process.env.BASE ?? '/',
  cleanUrls: true,
  lastUpdated: true,
  srcExclude: ['**/node_modules/**', '_template.md', '**/CLAUDE.md'],
  // README.md в каждой папке становится её индексной страницей
  rewrites: (id) => id.replace(/(^|\/)README\.md$/, '$1index.md'),
  // Ссылки на ноутбуки и исходники ведут в репозиторий, остальные битые ссылки не роняют сборку
  ignoreDeadLinks: true,
  markdown: {
    theme: { light: 'github-light', dark: 'github-dark' },
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
        // ```python run — блок с кнопкой «Запустить»;
        // ```python run session=имя — перед запуском выполняются предыдущие блоки с тем же именем
        const m = token.info.match(/^python\s+run\b(?:.*\bsession=([\w-]+))?/)
        if (!m) return defaultFence(tokens, idx, options, env, self)
        token.info = 'python'
        const html = defaultFence(tokens, idx, options, env, self)
        const session = m[1] ? ` session="${m[1]}"` : ''
        return `<RunPython code="${encodeURIComponent(token.content)}"${session}>${html}</RunPython>`
      }

      const defaultRender = md.renderer.rules.link_open
        ?? ((tokens, idx, options, _env, self) => self.renderToken(tokens, idx, options))
      md.renderer.rules.link_open = (tokens, idx, options, env, self) => {
        const href = tokens[idx].attrGet('href')
        if (href && !/^[a-z]+:|^#|^\//i.test(href) && !/\.md(#|$)/.test(href) && /\.\w+(#|$)/.test(href)) {
          const dir = path.posix.dirname(env.relativePath ?? '')
          tokens[idx].attrSet('href', `${REPO}/blob/main/${path.posix.normalize(path.posix.join(dir, href))}`)
          tokens[idx].attrSet('target', '_blank')
        }
        return defaultRender(tokens, idx, options, env, self)
      }
    },
  },
  themeConfig: {
    nav: [
      { text: 'Разделы', items: sections.map((s) => ({ text: s.text, link: `/${s.dir}/` })) },
    ],
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
    editLink: { pattern: `${REPO}/edit/main/:path`, text: 'Редактировать на GitHub' },
    docFooter: { prev: 'Назад', next: 'Дальше' },
    lastUpdated: { text: 'Обновлено' },
    darkModeSwitchLabel: 'Тема',
    sidebarMenuLabel: 'Меню',
    returnToTopLabel: 'Наверх',
  },
})
