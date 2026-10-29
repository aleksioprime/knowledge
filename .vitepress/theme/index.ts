import DefaultTheme from 'vitepress/theme'
import type { Theme } from 'vitepress'
import RunPython from './components/RunPython.vue'
import EventLoopDemo from './components/EventLoopDemo.vue'
import './style.css'

export default {
  extends: DefaultTheme,
  enhanceApp({ app }) {
    app.component('RunPython', RunPython)
    app.component('EventLoopDemo', EventLoopDemo)
  },
} satisfies Theme
