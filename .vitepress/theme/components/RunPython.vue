<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { runPython, stopPython } from '../python-runner'

const props = defineProps<{ code: string; session?: string }>()

const root = ref<HTMLElement>()
const original = decodeURIComponent(props.code).replace(/\n$/, '')
const source = ref(original)
const editing = ref(false)
const running = ref(false)
const status = ref('')
const lines = ref<{ kind: 'out' | 'err'; text: string }[]>([])

const changed = computed(() => source.value !== original)

// Код блоков той же цепочки, стоящих на странице выше этого (с учётом правок читателя)
function prelude() {
  if (!props.session) return []
  const blocks = [...document.querySelectorAll<HTMLElement>(`.run-python[data-session="${props.session}"]`)]
  return blocks.slice(0, blocks.indexOf(root.value!)).map((el) => el.dataset.source ?? '')
}

const continuation = ref(false)
onMounted(() => (continuation.value = prelude().length > 0))

// Вывод приходит кусками как есть; подряд идущие куски одного потока склеиваем
function append(kind: 'out' | 'err', text: string) {
  const last = lines.value.at(-1)
  if (last?.kind === kind) last.text += text
  else lines.value.push({ kind, text })
}

function run() {
  lines.value = []
  running.value = true
  runPython(source.value, (m) => {
    if (m.type === 'status') status.value = m.text
    else if (m.type === 'stdout') append('out', m.text)
    else if (m.type === 'stderr') append('err', m.text)
    else {
      running.value = false
      if (m.type === 'done') status.value = `Готово за ${m.text} с`
      else {
        status.value = 'Ошибка'
        append('err', (lines.value.length && !lines.value.at(-1)!.text.endsWith('\n') ? '\n' : '') + lastLines(m.text))
      }
    }
  }, prelude())
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
    source.value = source.value.slice(0, s) + '    ' + source.value.slice(end)
    requestAnimationFrame(() => el.setSelectionRange(s + 4, s + 4))
  }
}
</script>

<template>
  <div ref="root" class="run-python" :data-session="session" :data-source="source">
    <div v-if="continuation" class="session">Продолжение примера: перед запуском молча выполняются блоки выше</div>
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
      <button v-else class="btn danger" @click="stopPython">■ Остановить</button>
      <button class="btn" @click="editing = !editing">{{ editing ? 'Готово' : 'Изменить' }}</button>
      <button v-if="changed" class="btn" @click="source = original">Вернуть пример</button>
      <span class="status">{{ status }}</span>
      <span v-if="editing" class="hint">Ctrl/⌘ + Enter — запуск</span>
    </div>
    <pre v-if="lines.length || running" class="output"><span
      v-for="(l, i) in lines" :key="i" :class="l.kind">{{ l.text }}</span><span v-if="running" class="cursor">▍</span></pre>
  </div>
</template>

<style scoped>
.run-python {
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
.output .err { color: var(--vp-c-danger-1); }
.cursor { animation: blink 1s steps(2) infinite; color: var(--vp-c-text-3); }
@keyframes blink { 50% { opacity: 0; } }
</style>
