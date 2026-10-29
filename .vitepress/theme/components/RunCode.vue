<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { runCode, stopCode, type Lang } from '../runner'

const props = withDefaults(defineProps<{ code: string; lang?: Lang; session?: string; setup?: string; uses?: string }>(), {
  lang: 'python',
})

const root = ref<HTMLElement>()
const original = decodeURIComponent(props.code).replace(/\n$/, '')
const source = ref(original)
const editing = ref(false)
const running = ref(false)
const status = ref('')
type Item = { kind: 'out' | 'err'; text: string } | { kind: 'table'; fields: string[]; rows: unknown[][] }
const lines = ref<Item[]>([])

const changed = computed(() => source.value !== original)

// Код, который нужно молча выполнить перед блоком (с учётом правок читателя):
// подготовка (setup с именем из uses, а без uses — из session) и блоки той же цепочки session выше
function prelude() {
  const setup = props.uses ?? props.session
  if (!setup) return []
  const blocks = [...document.querySelectorAll<HTMLElement>(`.run-code[data-lang="${props.lang}"]`)]
  return blocks
    .slice(0, blocks.indexOf(root.value!))
    .filter((el) => el.dataset.setup === setup || (props.session && el.dataset.session === props.session))
    .map((el) => el.dataset.source ?? '')
}

const continuation = ref(false)
onMounted(() => (continuation.value = prelude().length > 0))

// Вывод приходит кусками как есть; подряд идущие куски одного потока склеиваем
function append(kind: 'out' | 'err', text: string) {
  const last = lines.value.at(-1)
  if (last && last.kind === kind) last.text += text
  else lines.value.push({ kind, text })
}

function run() {
  lines.value = []
  running.value = true
  runCode(props.lang, source.value, (m) => {
    if (m.type === 'table') lines.value.push({ kind: 'table', fields: m.fields, rows: m.rows })
    else if (m.type === 'status') status.value = m.text
    else if (m.type === 'stdout') append('out', m.text)
    else if (m.type === 'stderr') append('err', m.text)
    else {
      running.value = false
      if (m.type === 'done') status.value = `Готово за ${m.text} с`
      else {
        status.value = 'Ошибка'
        const last = lines.value.at(-1)
        const gap = last && last.kind !== 'table' && !last.text.endsWith('\n') ? '\n' : ''
        append('err', gap + lastLines(m.text))
      }
    }
  }, prelude())
}

// Ячейка таблицы: NULL, объекты (JSONB, массивы) и даты показываем читаемо
function cell(value: unknown) {
  if (value === null || value === undefined) return 'NULL'
  if (value instanceof Date) {
    const iso = value.toISOString()
    return iso.endsWith('T00:00:00.000Z') ? iso.slice(0, 10) : iso.replace('T', ' ').replace(/\.000Z$|Z$/, '')
  }
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

// У Pyodide в трассировке есть служебные кадры — оставляем то, что относится к коду заметки
function lastLines(text: string) {
  const idx = text.indexOf('File "<exec>"')
  return idx >= 0 ? 'Traceback:\n  ' + text.slice(idx).trim() : text.trim()
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
    e.preventDefault()
    run()
  } else if (e.key === 'Tab') {
    e.preventDefault()
    const el = e.target as HTMLTextAreaElement
    const { selectionStart: s, selectionEnd: end } = el
    const indent = props.lang === 'python' ? '    ' : '  '
    source.value = source.value.slice(0, s) + indent + source.value.slice(end)
    requestAnimationFrame(() => el.setSelectionRange(s + indent.length, s + indent.length))
  }
}
</script>

<template>
  <div
    ref="root"
    class="run-code"
    :data-lang="lang"
    :data-session="session"
    :data-setup="setup"
    :data-source="source"
  >
    <div v-if="continuation" class="session">
      {{ uses && !session ? 'Перед запуском молча выполняется подготовка выше' : 'Продолжение примера: перед запуском молча выполняются блоки выше' }}
    </div>
    <div v-show="!editing" class="view"><slot /></div>
    <textarea
      v-if="editing"
      v-model="source"
      class="editor"
      spellcheck="false"
      :rows="source.split('\n').length + 1"
      @keydown="onKeydown"
    />
    <div class="toolbar">
      <button v-if="!running" class="btn primary" @click="run">▶ Запустить</button>
      <button v-else class="btn danger" @click="stopCode(lang)">■ Остановить</button>
      <button class="btn" @click="editing = !editing">{{ editing ? 'Готово' : 'Изменить' }}</button>
      <button v-if="changed" class="btn" @click="source = original">Вернуть пример</button>
      <span class="status">{{ status }}</span>
      <span v-if="editing" class="hint">Ctrl/⌘ + Enter — запуск</span>
    </div>
    <div v-if="lines.length || running" class="output">
      <template v-for="(l, i) in lines" :key="i">
        <div v-if="l.kind === 'table'" class="table-wrap">
          <table>
            <thead><tr><th v-for="f in l.fields" :key="f">{{ f }}</th></tr></thead>
            <tbody>
              <tr v-for="(row, r) in l.rows" :key="r">
                <td v-for="(v, c) in row" :key="c" :class="{ null: v === null }">{{ cell(v) }}</td>
              </tr>
            </tbody>
          </table>
          <div class="rows-count">Строк: {{ l.rows.length }}</div>
        </div>
        <pre v-else :class="l.kind">{{ l.text }}</pre>
      </template>
      <span v-if="running" class="cursor">▍</span>
    </div>
  </div>
</template>

<style scoped>
.run-code {
  margin: 16px 0;
  border: 1px solid var(--vp-c-divider);
  border-radius: 8px;
  overflow: hidden;
}
.session {
  padding: 6px 16px;
  font-size: 12px;
  color: var(--vp-c-text-2);
  border-bottom: 1px solid var(--vp-c-divider);
  background: var(--vp-c-bg-soft);
}
.view :deep(div[class*='language-']) {
  margin: 0 !important;
  border-radius: 0 !important;
}
.editor {
  display: block;
  width: 100%;
  padding: 20px 24px;
  font-family: var(--vp-font-family-mono);
  font-size: var(--vp-code-font-size);
  line-height: var(--vp-code-line-height);
  background: var(--vp-code-block-bg);
  color: var(--vp-c-text-1);
  border: none;
  resize: vertical;
  white-space: pre;
  tab-size: 4;
  outline: none;
}
.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-top: 1px solid var(--vp-c-divider);
  background: var(--vp-c-bg-soft);
}
.btn {
  padding: 4px 12px;
  font-size: 13px;
  font-weight: 500;
  border: 1px solid var(--vp-c-divider);
  border-radius: 6px;
  background: var(--vp-c-bg);
  color: var(--vp-c-text-1);
  transition: border-color 0.2s;
}
.btn:hover { border-color: var(--vp-c-brand-1); }
.btn.primary { background: var(--vp-c-brand-3); border-color: var(--vp-c-brand-3); color: var(--vp-c-white); }
.btn.primary:hover { background: var(--vp-c-brand-2); }
.btn.danger { border-color: var(--vp-c-danger-1); color: var(--vp-c-danger-1); }
.status { font-size: 13px; color: var(--vp-c-text-2); }
.hint { margin-left: auto; font-size: 12px; color: var(--vp-c-text-3); }
.output {
  margin: 0;
  padding: 12px 16px;
  max-height: 320px;
  overflow: auto;
  font-family: var(--vp-font-family-mono);
  font-size: 13px;
  line-height: 1.6;
  border-top: 1px solid var(--vp-c-divider);
  background: var(--vp-c-bg);
  white-space: pre-wrap;
}
.output pre {
  margin: 0;
  font: inherit;
  white-space: pre-wrap;
  background: none;
}
.output .err { color: var(--vp-c-danger-1); }
.table-wrap { margin: 4px 0 12px; overflow-x: auto; }
.table-wrap table { display: table; margin: 0; font-size: 12.5px; border-collapse: collapse; }
.table-wrap th, .table-wrap td { padding: 4px 10px; border: 1px solid var(--vp-c-divider); white-space: pre; text-align: left; }
.table-wrap th { background: var(--vp-c-bg-soft); font-weight: 600; }
.table-wrap tr { background: none; border: none; }
.table-wrap td.null { color: var(--vp-c-text-3); font-style: italic; }
.rows-count { margin-top: 4px; font-size: 12px; color: var(--vp-c-text-3); }
.cursor { animation: blink 1s steps(2) infinite; color: var(--vp-c-text-3); }
@keyframes blink { 50% { opacity: 0; } }
</style>
