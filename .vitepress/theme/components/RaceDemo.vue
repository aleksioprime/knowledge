<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'

type State = 'running' | 'ready' | 'blocked' | 'done'
type Thread = { pc: number | null; reg: number | null; state: State }
type Step = { t1: Thread; t2: Thread; counter: number; lock: null | 'T1' | 'T2'; line: number; note: string }
type Scenario = { title: string; code: string[]; ops: string[]; steps: Step[] }

const code = (body: string[]) => [
  'from threading import Thread, Lock',
  '',
  'counter = 0',
  'lock = Lock()',
  '',
  'def work():',
  '    global counter',
  '    for _ in range(100_000):',
  ...body,
  '',
  't1, t2 = Thread(target=work), Thread(target=work)',
  't1.start(); t2.start()',
  't1.join(); t2.join()',
  'print(counter)',
]

const T = (pc: number | null, reg: number | null, state: State): Thread => ({ pc, reg, state })

const SCENARIOS: Record<string, Scenario> = {
  race: {
    title: 'Без Lock (ошибка)',
    code: code(['        counter += 1']),
    ops: ['читать counter', 'прибавить 1', 'записать counter'],
    steps: [
      { t1: T(0, 0, 'running'), t2: T(null, null, 'ready'), counter: 0, lock: null, line: 8, note: '<code>counter += 1</code> — не одна операция, а три: прочитать, прибавить, записать. <b>T1</b> держит GIL и читает <code>counter</code>: 0.' },
      { t1: T(1, 0, 'ready'), t2: T(0, 0, 'running'), counter: 0, lock: null, line: 8, note: 'Интерпретатор переключает GIL между потоками каждые 5 мс — между любыми двумя байткод-инструкциями. <b>T2</b> читает <code>counter</code> и тоже видит 0.' },
      { t1: T(1, 0, 'ready'), t2: T(1, 1, 'running'), counter: 0, lock: null, line: 8, note: '<b>T2</b> прибавляет единицу к своей копии: 1.' },
      { t1: T(1, 0, 'ready'), t2: T(2, 1, 'running'), counter: 1, lock: null, line: 8, note: '<b>T2</b> записывает 1 в <code>counter</code>.' },
      { t1: T(1, 1, 'running'), t2: T(null, null, 'ready'), counter: 1, lock: null, line: 8, note: 'GIL возвращается к <b>T1</b>. Он продолжает со старым значением 0 в руках и прибавляет к нему единицу: 1.' },
      { t1: T(2, 1, 'running'), t2: T(null, null, 'ready'), counter: 1, lock: null, line: 8, note: '<b>T1</b> записывает 1 поверх 1. Два увеличения — а счётчик вырос на один. Увеличение <b>T2</b> потеряно.' },
      { t1: T(null, null, 'done'), t2: T(null, null, 'done'), counter: 1, lock: null, line: 13, note: 'За 100 000 итераций таких наложений будут тысячи: <code>print(counter)</code> покажет меньше 200 000, и каждый запуск — разное число. GIL от этого не спасает: он защищает интерпретатор, а не ваши данные.' },
    ],
  },
  lock: {
    title: 'С Lock',
    code: code(['        with lock:', '            counter += 1']),
    ops: ['взять lock', 'читать counter', 'прибавить 1', 'записать counter', 'отдать lock'],
    steps: [
      { t1: T(0, null, 'running'), t2: T(null, null, 'ready'), counter: 0, lock: 'T1', line: 8, note: '<code>with lock:</code> — <b>T1</b> берёт блокировку. Теперь она занята, и это видно всем потокам.' },
      { t1: T(1, 0, 'running'), t2: T(null, null, 'ready'), counter: 0, lock: 'T1', line: 9, note: '<b>T1</b> читает <code>counter</code>: 0.' },
      { t1: T(1, 0, 'ready'), t2: T(0, null, 'blocked'), counter: 0, lock: 'T1', line: 8, note: 'GIL переключился на <b>T2</b>, но взять <code>lock</code> он не может — она у <b>T1</b>. <b>T2</b> засыпает в <code>acquire()</code> и отдаёт GIL обратно.' },
      { t1: T(2, 1, 'running'), t2: T(0, null, 'blocked'), counter: 0, lock: 'T1', line: 9, note: '<b>T1</b> прибавляет единицу: 1. Никто не может вклиниться между чтением и записью.' },
      { t1: T(3, 1, 'running'), t2: T(0, null, 'blocked'), counter: 1, lock: 'T1', line: 9, note: '<b>T1</b> записывает 1.' },
      { t1: T(4, null, 'running'), t2: T(0, null, 'ready'), counter: 1, lock: null, line: 8, note: 'Выход из <code>with</code> отдаёт блокировку. <b>T2</b> просыпается.' },
      { t1: T(null, null, 'ready'), t2: T(1, 1, 'running'), counter: 1, lock: 'T2', line: 9, note: '<b>T2</b> берёт блокировку и читает уже <b>новое</b> значение: 1.' },
      { t1: T(null, null, 'ready'), t2: T(3, 2, 'running'), counter: 2, lock: 'T2', line: 9, note: '<b>T2</b> прибавляет и записывает: 2.' },
      { t1: T(null, null, 'done'), t2: T(null, null, 'done'), counter: 2, lock: null, line: 13, note: 'Критическая секция выполняется целиком одним потоком. Результат всегда 200 000 — ценой того, что в ней потоки работают по очереди.' },
    ],
  },
}

const scenarioKey = ref<keyof typeof SCENARIOS>('race')
const scenario = computed(() => SCENARIOS[scenarioKey.value])
const index = ref(0)
const playing = ref(false)
const step = computed(() => scenario.value.steps[index.value])
const isLast = computed(() => index.value === scenario.value.steps.length - 1)
const thread = (name: 'T1' | 'T2') => (name === 'T1' ? step.value.t1 : step.value.t2)

const STATE_TITLE: Record<State, string> = { running: 'выполняется (GIL)', ready: 'ждёт GIL', blocked: 'ждёт lock', done: 'завершён' }

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
  index.value = Math.min(Math.max(index.value + d, 0), scenario.value.steps.length - 1)
}
watch(scenarioKey, () => {
  stopPlay()
  index.value = 0
})
onBeforeUnmount(stopPlay)
</script>

<template>
  <div class="demo race-demo">
    <div class="tabs">
      <button v-for="(s, key) in SCENARIOS" :key="key" :class="{ active: key === scenarioKey }" @click="scenarioKey = key">
        {{ s.title }}
      </button>
    </div>

    <div class="shared">
      <div class="box">
        <span class="box-title">counter</span>
        <span class="value">{{ step.counter }}</span>
      </div>
      <div v-if="scenarioKey === 'lock'" class="box lockbox" :class="{ held: step.lock }">
        <span class="box-title">lock</span>
        <span class="value">{{ step.lock ? `у ${step.lock}` : 'свободна' }}</span>
      </div>
    </div>

    <div class="threads">
      <div v-for="name in (['T1', 'T2'] as const)" :key="name" class="thread" :class="thread(name).state">
        <div class="thread-head">
          <b>{{ name }}</b>
          <span class="badge">{{ STATE_TITLE[thread(name).state] }}</span>
        </div>
        <ol class="ops">
          <li v-for="(op, i) in scenario.ops" :key="i" :class="{ active: thread(name).pc === i }">{{ op }}</li>
        </ol>
        <div class="reg">своя копия: <code>{{ thread(name).reg ?? '—' }}</code></div>
      </div>
    </div>

    <pre class="code"><code><span
      v-for="(l, i) in scenario.code" :key="i" class="line" :class="{ active: step.line === i }"
    >{{ l || ' ' }}
</span></code></pre>

    <p class="note" v-html="step.note" />

    <div class="controls">
      <button aria-label="В начало" @click="go(-99)">⏮</button>
      <button aria-label="Назад" @click="go(-1)">◀</button>
      <button class="play" @click="toggle">{{ playing ? '⏸ Пауза' : isLast ? '↻ Сначала' : '▶ Проиграть' }}</button>
      <button aria-label="Вперёд" @click="go(1)">▶</button>
      <span class="counter-label">Шаг {{ index + 1 }} из {{ scenario.steps.length }}</span>
    </div>
  </div>
</template>

<style scoped>
.shared { display: flex; gap: 12px; margin-bottom: 12px; }
.box {
  flex: 1;
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding: 8px 14px;
  border: 1px solid var(--vp-c-divider);
  border-radius: 8px;
  background: var(--vp-c-bg);
  font-family: var(--vp-font-family-mono);
}
.box-title { font-size: 12px; color: var(--vp-c-text-2); }
.value { font-size: 20px; font-weight: 600; transition: color 0.3s; }
.lockbox.held { border-color: var(--demo-waiting); }
.lockbox.held .value { color: var(--demo-waiting); }

.threads { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.thread {
  padding: 10px 12px;
  border: 2px solid var(--vp-c-divider);
  border-radius: 8px;
  background: var(--vp-c-bg);
  transition: border-color 0.4s, box-shadow 0.4s, opacity 0.4s;
}
.thread.running { border-color: var(--demo-running); box-shadow: 0 0 0 4px color-mix(in srgb, var(--demo-running) 20%, transparent); }
.thread.blocked { border-color: var(--demo-waiting); }
.thread.done { opacity: 0.6; }
.thread-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; font-family: var(--vp-font-family-mono); }
.badge { font-size: 11px; color: var(--vp-c-text-2); }
.ops { margin: 0; padding-left: 20px; font-size: 13px; line-height: 1.8; }
.ops li { padding: 0 6px; border-radius: 4px; transition: background 0.3s; }
.ops li.active { background: var(--vp-c-brand-soft); font-weight: 600; }
.reg { margin-top: 6px; font-size: 12px; color: var(--vp-c-text-2); }

.code {
  margin: 12px 0 0;
  padding: 10px 0;
  overflow-x: auto;
  border-radius: 8px;
  background: var(--vp-code-block-bg);
  font-family: var(--vp-font-family-mono);
  font-size: 12.5px;
  line-height: 1.6;
}
.line { display: block; padding: 0 12px; border-left: 3px solid transparent; transition: background 0.3s; }
.line.active { background: var(--vp-c-brand-soft); border-left-color: var(--vp-c-brand-1); }

@media (max-width: 640px) {
  .threads { grid-template-columns: 1fr; }
}
</style>
