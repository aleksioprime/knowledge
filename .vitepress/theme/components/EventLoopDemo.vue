<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'

type Zone = 'ready' | 'running' | 'waiting' | 'done'
type Step = {
  t: number
  ready?: string[]
  running?: string
  waiting?: Record<string, string>
  done?: string[]
  line: number | null
  out?: string
  note: string
}
type Scenario = { title: string; code: string[]; total: number; steps: Step[] }

const TASKS = ['main', 'A', 'B']
const ZONES: { key: Zone; title: string }[] = [
  { key: 'ready', title: 'Готовы' },
  { key: 'running', title: 'Выполняется' },
  { key: 'waiting', title: 'Ожидают' },
  { key: 'done', title: 'Завершены' },
]

const codeFor = (sleep: string) => [
  sleep === 'await asyncio.sleep' ? 'import asyncio' : 'import asyncio, time',
  '',
  'async def fetch(name, delay):',
  "    print(f'{name}: запрос')",
  `    ${sleep}(delay)`,
  "    print(f'{name}: ответ')",
  '',
  'async def main():',
  "    await asyncio.gather(fetch('A', 2), fetch('B', 1))",
  '',
  'asyncio.run(main())',
]

// Общее начало обоих сценариев: main запускает gather и встаёт на ожидание
const start: Step[] = [
  { t: 0, ready: ['main'], line: 10, note: '<code>asyncio.run</code> создаёт цикл событий и кладёт задачу <b>main</b> в очередь готовых.' },
  { t: 0, running: 'main', ready: ['A', 'B'], line: 8, note: 'Цикл берёт <b>main</b> из очереди. <code>gather</code> оборачивает обе корутины в задачи <b>A</b> и <b>B</b> и ставит их в очередь.' },
  { t: 0, ready: ['A', 'B'], waiting: { main: 'ждёт gather' }, line: 8, note: '<b>main</b> дошла до <code>await</code>: результата ещё нет, поэтому она отдаёт управление циклу.' },
  { t: 0, running: 'A', ready: ['B'], waiting: { main: 'ждёт gather' }, line: 3, out: 'A: запрос', note: 'Цикл берёт следующую готовую задачу — <b>A</b>. Она печатает строку.' },
]

const SCENARIOS: Record<string, Scenario> = {
  async: {
    title: 'await asyncio.sleep',
    code: codeFor('await asyncio.sleep'),
    total: 2,
    steps: [
      ...start,
      { t: 0, ready: ['B'], waiting: { main: 'ждёт gather', A: 'таймер до 2 с' }, line: 4, note: '<code>await asyncio.sleep(2)</code> не держит поток: цикл заводит таймер и снимает <b>A</b> с выполнения.' },
      { t: 0, running: 'B', waiting: { main: 'ждёт gather', A: 'таймер до 2 с' }, line: 3, out: 'B: запрос', note: 'Поток свободен, и цикл сразу запускает <b>B</b>.' },
      { t: 0, waiting: { main: 'ждёт gather', A: 'таймер до 2 с', B: 'таймер до 1 с' }, line: 4, note: '<b>B</b> тоже уходит ждать. Обе задержки теперь идут <b>одновременно</b>.' },
      { t: 1, ready: ['B'], waiting: { main: 'ждёт gather', A: 'таймер до 2 с' }, line: null, note: 'Готовых задач нет — цикл спит до ближайшего таймера. Через 1 с таймер <b>B</b> срабатывает, задача снова в очереди.' },
      { t: 1, running: 'B', waiting: { main: 'ждёт gather', A: 'таймер до 2 с' }, line: 5, out: 'B: ответ', note: '<b>B</b> продолжает с места, где остановилась, — со строки после <code>await</code>.' },
      { t: 1, waiting: { main: 'ждёт gather', A: 'таймер до 2 с' }, done: ['B'], line: null, note: '<b>B</b> завершилась. <b>A</b> ждёт ещё секунду.' },
      { t: 2, ready: ['A'], waiting: { main: 'ждёт gather' }, done: ['B'], line: null, note: 'На отметке 2 с срабатывает таймер <b>A</b>.' },
      { t: 2, running: 'A', waiting: { main: 'ждёт gather' }, done: ['B'], line: 5, out: 'A: ответ', note: '<b>A</b> печатает ответ.' },
      { t: 2, ready: ['main'], done: ['B', 'A'], line: null, note: 'Все задачи <code>gather</code> готовы — <b>main</b> возвращается в очередь.' },
      { t: 2, done: ['B', 'A', 'main'], line: 10, note: 'Итого <b>2 секунды</b>, а не 3: пока одна задача ждала, работала другая.' },
    ],
  },
  blocking: {
    title: 'time.sleep (ошибка)',
    code: codeFor('time.sleep'),
    total: 3,
    steps: [
      ...start,
      { t: 0, running: 'A', ready: ['B'], waiting: { main: 'ждёт gather' }, line: 4, note: '<code>time.sleep(2)</code> — обычный блокирующий вызов. Он не отдаёт управление циклу, и цикл не может переключиться.' },
      { t: 2, running: 'A', ready: ['B'], waiting: { main: 'ждёт gather' }, line: 4, note: 'Прошло 2 секунды. Всё это время <b>B</b> стояла в очереди, хотя могла уже начать.' },
      { t: 2, running: 'A', ready: ['B'], waiting: { main: 'ждёт gather' }, line: 5, out: 'A: ответ', note: '<b>A</b> наконец отвечает.' },
      { t: 2, running: 'B', waiting: { main: 'ждёт gather' }, done: ['A'], line: 3, out: 'B: запрос', note: 'Только теперь цикл запускает <b>B</b>.' },
      { t: 3, running: 'B', waiting: { main: 'ждёт gather' }, done: ['A'], line: 4, note: 'И снова поток заблокирован на секунду.' },
      { t: 3, running: 'B', waiting: { main: 'ждёт gather' }, done: ['A'], line: 5, out: 'B: ответ', note: '<b>B</b> отвечает.' },
      { t: 3, done: ['A', 'B', 'main'], line: 10, note: 'Итого <b>3 секунды</b> — сумма всех задержек, как в обычном синхронном коде. В веб-сервисе так «замирают» все запросы сразу.' },
    ],
  },
}

const scenarioKey = ref<keyof typeof SCENARIOS>('async')
const scenario = computed(() => SCENARIOS[scenarioKey.value])
const index = ref(0)
const playing = ref(false)
const step = computed(() => scenario.value.steps[index.value])
const isLast = computed(() => index.value === scenario.value.steps.length - 1)

const output = computed(() =>
  scenario.value.steps.slice(0, index.value + 1).flatMap((s) => (s.out ? [s.out] : [])),
)

// Положение фишки задачи: колонка зоны и порядковый номер внутри неё
const chips = computed(() => {
  const s = step.value
  const lists: Record<Zone, string[]> = {
    ready: s.ready ?? [],
    running: s.running ? [s.running] : [],
    waiting: Object.keys(s.waiting ?? {}),
    done: s.done ?? [],
  }
  return TASKS.map((name) => {
    const zi = ZONES.findIndex((z) => lists[z.key].includes(name))
    if (zi < 0) return { name, visible: false, zone: 'ready' as Zone, left: '0%', top: 44, label: '' }
    const zone = ZONES[zi].key
    return {
      name,
      visible: true,
      zone,
      left: `calc(${zi * 25}% + 6px)`,
      top: 44 + lists[zone].indexOf(name) * 46,
      label: s.waiting?.[name] ?? '',
    }
  })
})

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
  }, 1800)
}
const toggle = () => (playing.value ? stopPlay() : play())
const go = (d: number) => {
  stopPlay()
  index.value = Math.min(Math.max(index.value + d, 0), scenario.value.steps.length - 1)
}

watch(scenarioKey, () => {
  stopPlay()
  index.value = 0
})
onBeforeUnmount(stopPlay)
</script>

<template>
  <div class="loop-demo">
    <div class="tabs" role="tablist">
      <button
        v-for="(s, key) in SCENARIOS" :key="key" role="tab"
        :class="{ active: scenarioKey === key }" :aria-selected="scenarioKey === key"
        @click="scenarioKey = key"
      >{{ s.title }}</button>
    </div>

    <div class="clock">
      <span class="clock-label">Время</span>
      <div class="axis">
        <div class="fill" :style="{ width: `${(step.t / 3) * 100}%` }" />
        <span v-for="n in 4" :key="n" class="tick" :style="{ left: `${((n - 1) / 3) * 100}%` }">{{ n - 1 }} с</span>
      </div>
    </div>

    <div class="stage">
      <div v-for="z in ZONES" :key="z.key" class="zone" :class="z.key">
        <div class="zone-title">{{ z.title }}</div>
      </div>
      <div
        v-for="c in chips" :key="c.name" class="chip" :class="[c.zone, { hidden: !c.visible }]"
        :style="{ left: c.left, top: `${c.top}px` }"
      >
        <b>{{ c.name }}</b>
        <small v-if="c.label">{{ c.label }}</small>
      </div>
    </div>

    <div class="panels">
      <pre class="code"><code><span
        v-for="(l, i) in scenario.code" :key="i" class="line" :class="{ active: step.line === i }"
      >{{ l || ' ' }}
</span></code></pre>
      <pre class="console"><span class="console-title">Вывод</span>
<span v-for="(o, i) in output" :key="i" class="console-line">{{ o }}
</span></pre>
    </div>

    <p class="note" v-html="step.note" />

    <div class="controls">
      <button aria-label="В начало" @click="go(-99)">⏮</button>
      <button aria-label="Назад" @click="go(-1)">◀</button>
      <button class="play" @click="toggle">{{ playing ? '⏸ Пауза' : isLast ? '↻ Сначала' : '▶ Проиграть' }}</button>
      <button aria-label="Вперёд" @click="go(1)">▶</button>
      <span class="counter">Шаг {{ index + 1 }} из {{ scenario.steps.length }}</span>
    </div>
  </div>
</template>

<style scoped>
.loop-demo {
  margin: 24px 0;
  padding: 16px;
  border: 1px solid var(--vp-c-divider);
  border-radius: 12px;
  background: var(--vp-c-bg-soft);
}
.tabs { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 16px; }
.tabs button {
  padding: 4px 12px;
  font-family: var(--vp-font-family-mono);
  font-size: 13px;
  border: 1px solid var(--vp-c-divider);
  border-radius: 999px;
  color: var(--vp-c-text-2);
}
.tabs button.active { border-color: var(--vp-c-brand-1); color: var(--vp-c-brand-1); background: var(--vp-c-brand-soft); }

.clock { display: flex; align-items: center; gap: 12px; margin-bottom: 28px; }
.clock-label { font-size: 12px; color: var(--vp-c-text-2); }
.axis { position: relative; flex: 1; height: 6px; margin-right: 16px; border-radius: 3px; background: var(--vp-c-divider); }
.fill { height: 100%; border-radius: 3px; background: var(--vp-c-brand-1); transition: width 0.9s ease-in-out; }
.tick { position: absolute; top: 10px; transform: translateX(-50%); font-size: 11px; white-space: nowrap; color: var(--vp-c-text-3); }
.tick:first-of-type { transform: none; }
.tick:last-of-type { transform: translateX(-100%); }

.stage { position: relative; display: grid; grid-template-columns: repeat(4, 1fr); height: 190px; }
.zone { margin: 0 3px; border: 1px dashed var(--vp-c-divider); border-radius: 8px; }
.zone-title { padding: 8px; font-size: 12px; font-weight: 600; text-align: center; color: var(--vp-c-text-2); }
.zone.running { border-style: solid; border-color: var(--demo-running); }

.chip {
  position: absolute;
  width: calc(25% - 12px);
  height: 40px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  border: 2px solid var(--chip);
  background: var(--vp-c-bg);
  font-family: var(--vp-font-family-mono);
  font-size: 13px;
  line-height: 1.2;
  transition: left 0.6s ease-in-out, top 0.6s ease-in-out, opacity 0.4s, border-color 0.4s, transform 0.4s;
}
.chip small { font-family: var(--vp-font-family-base); font-size: 10px; color: var(--vp-c-text-2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; padding: 0 4px; }
.chip.ready { --chip: var(--demo-ready); }
.chip.running { --chip: var(--demo-running); box-shadow: 0 0 0 4px color-mix(in srgb, var(--demo-running) 20%, transparent); }
.chip.waiting { --chip: var(--demo-waiting); }
.chip.done { --chip: var(--demo-done); opacity: 0.6; }
.chip.hidden { opacity: 0; transform: scale(0.6); }

.panels { display: grid; grid-template-columns: 2fr 1fr; gap: 12px; margin-top: 12px; }
.panels pre {
  margin: 0;
  padding: 12px 0;
  overflow-x: auto;
  border-radius: 8px;
  background: var(--vp-code-block-bg);
  font-family: var(--vp-font-family-mono);
  font-size: 12.5px;
  line-height: 1.7;
}
.line { display: block; padding: 0 12px; border-left: 3px solid transparent; transition: background 0.3s; }
.line.active { background: var(--vp-c-brand-soft); border-left-color: var(--vp-c-brand-1); }
.console { padding: 12px !important; }
.console-title { font-size: 11px; color: var(--vp-c-text-3); }
.console-line { animation: appear 0.4s; }
@keyframes appear { from { opacity: 0; transform: translateY(4px); } }

.note { min-height: 3.2em; margin: 16px 0 12px; line-height: 1.6; }

.controls { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
.controls button {
  min-width: 36px;
  padding: 4px 10px;
  border: 1px solid var(--vp-c-divider);
  border-radius: 6px;
  background: var(--vp-c-bg);
}
.controls button:hover { border-color: var(--vp-c-brand-1); }
.controls .play { background: var(--vp-c-brand-3); border-color: var(--vp-c-brand-3); color: var(--vp-c-white); }
.counter { margin-left: auto; font-size: 12px; color: var(--vp-c-text-2); }

@media (max-width: 640px) {
  .panels { grid-template-columns: 1fr; }
  .zone-title { font-size: 10px; padding: 8px 2px; }
  .chip small { font-size: 9px; }
}
</style>
