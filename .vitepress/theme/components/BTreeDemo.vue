<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'

// Учебное B-дерево: корень → внутренние узлы → листья. В листьях ключи со ссылками на строки таблицы (TID),
// листья связаны в список — по нему идёт сканирование диапазона
const ROOT = [30, 60]
const INTERNAL = [[10, 20], [40, 50], [70, 80]]
const LEAVES = [[1, 4, 7], [10, 13, 16], [20, 23, 27], [30, 33, 37], [40, 43, 47], [50, 53, 57], [60, 63, 67], [70, 74, 78], [80, 85, 90]]

type Node = { level: 0 | 1 | 2; index: number }
type Step = { node?: Node; key?: number; found: number[]; leaves: number[]; note: string }
type Query = { title: string; sql: string; steps: Step[] }

// Ребёнок, в который ведёт значение: child[i] хранит ключи от keys[i-1] до keys[i]
const childFor = (keys: number[], v: number) => keys.filter((k) => v >= k).length

function descend(v: number, steps: Step[]) {
  const c = childFor(ROOT, v)
  const where = c === 0 ? `меньше ${ROOT[0]}` : c === 1 ? `между ${ROOT[0]} и ${ROOT[1]}` : `не меньше ${ROOT[1]}`
  steps.push({ node: { level: 0, index: 0 }, found: [], leaves: [], note: `Корень: ключи ${ROOT.join(', ')}. Значение ${v} ${where} — идём в ${c + 1}-го ребёнка. Корень почти всегда в кэше: это одна страница.` })
  const l = c * 3 + childFor(INTERNAL[c], v)
  steps.push({ node: { level: 1, index: c }, found: [], leaves: [], note: `Внутренний узел: ключи ${INTERNAL[c].join(', ')}. Ещё одно сравнение — и известен лист. Для миллиона строк в дереве всего 3–4 уровня.` })
  return l
}

function pointLookup(v: number): Step[] {
  const steps: Step[] = []
  const l = descend(v, steps)
  const leaf = LEAVES[l]
  const hit = leaf.includes(v)
  steps.push({ node: { level: 2, index: l }, key: hit ? v : undefined, found: hit ? [v] : [], leaves: [l], note: hit
    ? `Лист: ключи ${leaf.join(', ')}. Ключ ${v} найден, рядом с ним TID — номер страницы и позиция строки в таблице.`
    : `Лист: ключи ${leaf.join(', ')}. Ключа ${v} нет, и больше искать негде: если бы он был, лежал бы именно здесь. Три страницы прочитано, результат пуст.` })
  if (hit) steps.push({ found: [v], leaves: [l], note: 'По TID читается страница таблицы (heap) и проверяется, видна ли строка транзакции. Итого 4 страницы вместо чтения всей таблицы.' })
  return steps
}

function rangeScan(from: number, to: number | null, label: string, finale: string): Step[] {
  const steps: Step[] = []
  let l = descend(from, steps)
  const found: number[] = []
  const leaves: number[] = []
  for (;;) {
    leaves.push(l)
    const keys = LEAVES[l].filter((k) => k >= from && (to === null || k <= to))
    found.push(...keys)
    const last = LEAVES[l][LEAVES[l].length - 1]
    const more = to === null ? l + 1 < LEAVES.length : last <= to
    steps.push({ node: { level: 2, index: l }, found: [...found], leaves: [...leaves], note: more
      ? `Лист ${l + 1}: подходят ${keys.join(', ') || 'ничего'}. Условие ${label} ещё выполняется — переходим по ссылке к соседнему листу, в корень возвращаться не нужно.`
      : `Лист ${l + 1}: подходят ${keys.join(', ') || 'ничего'}. ${to === null ? 'Листья закончились' : `Дальше ключи больше ${to}`} — сканирование завершено.` })
    if (!more) break
    l++
  }
  steps.push({ found, leaves, note: finale })
  return steps
}

const QUERIES: Record<string, Query> = {
  point: { title: 'id = 47', sql: 'SELECT * FROM tasks WHERE id = 47', steps: pointLookup(47) },
  missing: { title: 'id = 48', sql: 'SELECT * FROM tasks WHERE id = 48', steps: pointLookup(48) },
  range: {
    title: 'BETWEEN 40 AND 55',
    sql: 'SELECT * FROM tasks WHERE id BETWEEN 40 AND 55',
    steps: rangeScan(40, 55, 'id ≤ 55', 'Спуск от корня один, дальше листья читаются подряд по ссылкам. Для каждого найденного TID читается строка таблицы, поэтому диапазон на тысячу строк стоит заметно дороже, чем на пять.'),
  },
  wide: {
    title: 'id > 5',
    sql: 'SELECT * FROM tasks WHERE id > 5',
    steps: rangeScan(6, null, 'id > 5', 'Прочитаны почти все листья и почти все строки таблицы, причём строки — вразнобой по TID. Планировщик предвидит это по статистике и выбирает Seq Scan: прочитать таблицу подряд дешевле, чем прыгать по ней через индекс.'),
  },
}

const queryKey = ref<keyof typeof QUERIES>('point')
const query = computed(() => QUERIES[queryKey.value])
const index = ref(0)
const playing = ref(false)
const step = computed(() => query.value.steps[index.value])
const isLast = computed(() => index.value === query.value.steps.length - 1)
// Корень и внутренний узел — по странице, дальше по странице на каждый пройденный лист
const pagesRead = computed(() => {
  const level = step.value.node?.level
  return level === 0 ? 1 : level === 1 ? 2 : 2 + step.value.leaves.length
})

const isActive = (level: number, i: number) => step.value.node?.level === level && step.value.node.index === i
const isVisited = (i: number) => step.value.leaves.includes(i)
const isFound = (k: number) => step.value.found.includes(k)

let timer: ReturnType<typeof setInterval> | undefined
function stopPlay() {
  playing.value = false
  clearInterval(timer)
}
function play() {
  if (isLast.value) index.value = 0
  playing.value = true
  timer = setInterval(() => {
    if (isLast.value) stopPlay()
    else index.value++
  }, 2200)
}
const toggle = () => (playing.value ? stopPlay() : play())
const go = (d: number) => {
  stopPlay()
  index.value = Math.min(Math.max(index.value + d, 0), query.value.steps.length - 1)
}
watch(queryKey, () => {
  stopPlay()
  index.value = 0
})
onBeforeUnmount(stopPlay)
</script>

<template>
  <div class="demo btree-demo">
    <div class="tabs">
      <button v-for="(q, key) in QUERIES" :key="key" :class="{ active: key === queryKey }" @click="queryKey = key">{{ q.title }}</button>
    </div>
    <pre class="sql"><code>{{ query.sql }}</code></pre>

    <div class="tree">
      <div class="level">
        <div class="node" :class="{ active: isActive(0, 0) }">
          <span v-for="k in ROOT" :key="k" class="key">{{ k }}</span>
        </div>
      </div>
      <div class="level">
        <div v-for="(keys, i) in INTERNAL" :key="i" class="node" :class="{ active: isActive(1, i) }">
          <span v-for="k in keys" :key="k" class="key">{{ k }}</span>
        </div>
      </div>
      <div class="level leaves">
        <template v-for="(keys, i) in LEAVES" :key="i">
          <div class="node leaf" :class="{ active: isActive(2, i), visited: isVisited(i) }">
            <span v-for="k in keys" :key="k" class="key" :class="{ found: isFound(k), hit: step.key === k }">{{ k }}</span>
          </div>
          <span v-if="i < LEAVES.length - 1" class="link" :class="{ visited: isVisited(i) && isVisited(i + 1) }">→</span>
        </template>
      </div>
      <div class="legend">
        <span>листья связаны в список, в них — ключ и TID строки</span>
        <span class="stat">страниц индекса: {{ pagesRead }}</span>
        <span class="stat">строк найдено: {{ step.found.length }}</span>
      </div>
    </div>

    <p class="note" v-html="step.note" />

    <div class="controls">
      <button aria-label="В начало" @click="go(-99)">⏮</button>
      <button aria-label="Назад" @click="go(-1)">◀</button>
      <button class="play" @click="toggle">{{ playing ? '⏸ Пауза' : isLast ? '↻ Сначала' : '▶ Проиграть' }}</button>
      <button aria-label="Вперёд" @click="go(1)">▶</button>
      <span class="counter-label">Шаг {{ index + 1 }} из {{ query.steps.length }}</span>
    </div>
  </div>
</template>

<style scoped>
.sql { margin: 0 0 12px; padding: 8px 12px; border-radius: 8px; background: var(--vp-code-block-bg); font-family: var(--vp-font-family-mono); font-size: 12.5px; }

.tree { padding: 8px 4px; overflow-x: auto; }
.level { display: flex; justify-content: safe center; gap: 18px; margin-bottom: 22px; min-width: 560px; }
.level.leaves { gap: 0; margin-bottom: 8px; align-items: center; }
.node {
  display: flex; gap: 2px; padding: 4px; border: 2px solid var(--vp-c-divider); border-radius: 6px; background: var(--vp-c-bg);
  transition: border-color 0.4s, box-shadow 0.4s;
}
.node.active { border-color: var(--demo-running); box-shadow: 0 0 0 4px color-mix(in srgb, var(--demo-running) 20%, transparent); }
.node.visited { border-color: var(--demo-ready); }
.leaf { padding: 3px; }
.key {
  min-width: 26px; padding: 2px 4px; border-radius: 4px; background: var(--vp-c-default-soft);
  font-family: var(--vp-font-family-mono); font-size: 12px; text-align: center; transition: background 0.3s, color 0.3s;
}
.leaf .key { min-width: 20px; padding: 2px; font-size: 11px; }
.key.found { background: color-mix(in srgb, var(--demo-running) 25%, transparent); }
.key.hit { background: var(--demo-running); color: var(--vp-c-white); }
.link { padding: 0 2px; font-size: 11px; color: var(--vp-c-text-3); transition: color 0.3s; }
.link.visited { color: var(--demo-ready); font-weight: 700; }
.legend { display: flex; flex-wrap: wrap; gap: 16px; font-size: 11px; color: var(--vp-c-text-3); }
.stat { font-family: var(--vp-font-family-mono); color: var(--vp-c-text-2); }
</style>
