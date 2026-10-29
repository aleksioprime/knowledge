import DefaultTheme from 'vitepress/theme'
import type { Theme } from 'vitepress'
import RunCode from './components/RunCode.vue'
import EventLoopDemo from './components/EventLoopDemo.vue'
import RaceDemo from './components/RaceDemo.vue'
import KafkaDemo from './components/KafkaDemo.vue'
import BTreeDemo from './components/BTreeDemo.vue'
import './style.css'

export default {
  extends: DefaultTheme,
  enhanceApp({ app }) {
    app.component('RunCode', RunCode)
    app.component('EventLoopDemo', EventLoopDemo)
    app.component('RaceDemo', RaceDemo)
    app.component('KafkaDemo', KafkaDemo)
    app.component('BTreeDemo', BTreeDemo)
  },
} satisfies Theme
