<script setup lang="ts">
import { computed, reactive, ref } from 'vue'

// Интерактивная модель топика: 3 партиции и две независимые группы потребителей
const PARTITIONS = 3
const KEYS = ['task-1', 'task-2', 'task-3', 'task-4', 'task-5', 'task-6']
type Message = { key: string; offset: number }
type Group = { name: string; consumers: number; offsets: number[]; color: string; max: number }

const partitions = reactive<Message[][]>(Array.from({ length: PARTITIONS }, () => []))
const groups = reactive<Group[]>([
  { name: 'analytics', consumers: 2, offsets: [0, 0, 0], color: 'var(--demo-ready)', max: 4 },
  { name: 'mailer', consumers: 1, offsets: [0, 0, 0], color: 'var(--demo-waiting)', max: 1 },
])
const log = ref<string[]>(['Топик пуст. Отправьте событие — оно попадёт в партицию по ключу.'])
let keyIndex = 0

// Партиция по ключу: в Kafka это murmur2(key) % число партиций, здесь — сумма кодов символов
function partitionOf(key: string) {
  return [...key].reduce((h, ch) => h + ch.charCodeAt(0), 0) % PARTITIONS
}

// Партиции группы раздаются потребителям по кругу; потребители сверх числа партиций простаивают
function assigned(group: Group, consumer: number) {
  return Array.from({ length: PARTITIONS }, (_, p) => p).filter((p) => p % group.consumers === consumer)
}
const lag = (group: Group, p: number) => partitions[p].length - group.offsets[p]

function say(line: string) {
  log.value = [line, ...log.value].slice(0, 6)
}

function produce() {
  const key = KEYS[keyIndex++ % KEYS.length]
  const p = partitionOf(key)
  partitions[p].push({ key, offset: partitions[p].length })
  say(`Производитель → ${key}: hash(key) % ${PARTITIONS} = ${p}, партиция P${p}, offset ${partitions[p].length - 1}`)
}

function consume(group: Group) {
  const read: string[] = []
  for (let c = 0; c < group.consumers; c++) {
    for (const p of assigned(group, c)) {
      const msg = partitions[p][group.offsets[p]]
      if (!msg) continue
      group.offsets[p]++
      read.push(`C${c + 1} ← ${msg.key} (P${p}, offset ${msg.offset})`)
    }
  }
  say(read.length ? `Группа ${group.name}: ${read.join('; ')}` : `Группа ${group.name}: новых сообщений нет, лаг 0`)
}

function resize(group: Group, delta: number) {
  group.consumers = Math.min(Math.max(group.consumers + delta, 1), group.max)
  const parts = Array.from({ length: group.consumers }, (_, c) => `C${c + 1}: ${assigned(group, c).map((p) => `P${p}`).join(', ') || 'простаивает'}`)
  say(`Ребалансировка группы ${group.name}: ${parts.join('; ')}. Смещения сохранены — чтение продолжится с них.`)
}

function reset() {
  partitions.forEach((p) => p.splice(0))
  groups.forEach((g) => g.offsets.fill(0))
  keyIndex = 0
  log.value = ['Топик очищен.']
}

const CELL = 58
const maxLen = computed(() => Math.max(4, ...partitions.map((p) => p.length)))
</script>

<template>
  <div class="demo kafka-demo">
    <div class="controls">
      <button class="play" @click="produce">＋ Отправить событие</button>
      <button @click="reset">Очистить</button>
    </div>

    <div class="topic">
      <div class="topic-title">topic <code>task_events</code></div>
      <div v-for="(msgs, p) in partitions" :key="p" class="partition">
        <div class="partition-name">P{{ p }}</div>
        <div class="cells" :style="{ width: `${maxLen * CELL}px` }">
          <div v-for="m in msgs" :key="m.offset" class="cell" :style="{ width: `${CELL - 4}px` }">
            <b>{{ m.key }}</b>
            <small>offset {{ m.offset }}</small>
          </div>
          <div
            v-for="(g, gi) in groups" :key="g.name" class="marker"
            :style="{ left: `${g.offsets[p] * CELL}px`, top: `${46 + gi * 13}px`, color: g.color }"
            :title="`${g.name}: следующее — offset ${g.offsets[p]}`"
          >▲ <small>{{ g.name }}</small></div>
        </div>
      </div>
    </div>

    <div class="groups">
      <div v-for="g in groups" :key="g.name" class="group" :style="{ borderColor: g.color }">
        <div class="group-head">
          <b>группа <code>{{ g.name }}</code></b>
          <span class="controls group-tools">
            <template v-if="g.max > 1">
              <button aria-label="Убрать потребителя" :disabled="g.consumers <= 1" @click="resize(g, -1)">−</button>
              <span>{{ g.consumers }}</span>
              <button aria-label="Добавить потребителя" :disabled="g.consumers >= g.max" @click="resize(g, 1)">+</button>
            </template>
            <button class="play" @click="consume(g)">Прочитать</button>
          </span>
        </div>
        <ul class="consumers">
          <li v-for="c in g.consumers" :key="c">
            C{{ c }} →
            <template v-if="assigned(g, c - 1).length">
              <span v-for="p in assigned(g, c - 1)" :key="p" class="pill">P{{ p }} <small>лаг {{ lag(g, p) }}</small></span>
            </template>
            <span v-else class="idle">без партиций, простаивает</span>
          </li>
        </ul>
      </div>
    </div>

    <pre class="log"><span v-for="(l, i) in log" :key="l + i" class="log-line">{{ l }}
</span></pre>
  </div>
</template>

<style scoped>
.kafka-demo .controls { margin-bottom: 12px; }
.group-tools { margin: 0; }
.group-tools button:disabled { opacity: 0.4; }

.topic { padding: 10px 12px 18px; border: 1px dashed var(--vp-c-divider); border-radius: 8px; overflow-x: auto; }
.topic-title { margin-bottom: 8px; font-size: 12px; color: var(--vp-c-text-2); }
.partition { display: flex; align-items: flex-start; gap: 8px; margin-bottom: 34px; }
.partition:last-child { margin-bottom: 12px; }
.partition-name { width: 28px; padding-top: 10px; font-family: var(--vp-font-family-mono); font-size: 12px; color: var(--vp-c-text-2); }
.cells { position: relative; display: flex; gap: 4px; min-height: 42px; padding-bottom: 4px; border-bottom: 1px solid var(--vp-c-divider); }
.cell {
  display: flex; flex-direction: column; align-items: center; justify-content: center; flex: none;
  height: 40px; border: 1px solid var(--vp-c-divider); border-radius: 6px; background: var(--vp-c-bg);
  font-family: var(--vp-font-family-mono); font-size: 11px; animation: appear 0.3s;
}
.cell small { font-size: 9px; color: var(--vp-c-text-3); }
@keyframes appear { from { opacity: 0; transform: scale(0.7); } }
.marker { position: absolute; font-size: 10px; line-height: 1; white-space: nowrap; transition: left 0.5s ease-in-out; }
.marker small { font-size: 9px; }

.groups { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 12px; }
.group { padding: 10px 12px; border: 2px solid; border-radius: 8px; background: var(--vp-c-bg); }
.group-head { display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap; }
.consumers { margin: 8px 0 0; padding: 0; list-style: none; font-family: var(--vp-font-family-mono); font-size: 12px; line-height: 2; }
.pill { display: inline-block; margin-left: 4px; padding: 0 8px; border-radius: 999px; background: var(--vp-c-default-soft); }
.pill small { color: var(--vp-c-text-2); }
.idle { color: var(--vp-c-text-3); }

.log { margin: 12px 0 0; padding: 10px 12px; border-radius: 8px; background: var(--vp-code-block-bg); font-size: 12px; line-height: 1.6; white-space: pre-wrap; }
.log-line { color: var(--vp-c-text-3); }
.log-line:first-child { color: var(--vp-c-text-1); }

@media (max-width: 640px) {
  .groups { grid-template-columns: 1fr; }
}
</style>
