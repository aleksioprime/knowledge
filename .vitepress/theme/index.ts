import DefaultTheme from 'vitepress/theme'
import type { Theme } from 'vitepress'
import RunCode from './components/RunCode.vue'
import EventLoopDemo from './components/EventLoopDemo.vue'
import './style.css'

export default {
  extends: DefaultTheme,
  enhanceApp({ app }) {
    app.component('RunCode', RunCode)
    app.component('EventLoopDemo', EventLoopDemo)
  },
} satisfies Theme
