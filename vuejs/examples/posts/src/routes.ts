import { createRouter, createWebHistory } from 'vue-router'

import { useAuthStore } from '@/store/auth.store'
import AllPostsView from '@/views/AllPostsView.vue'
import MyPostsView from '@/views/MyPostsView.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'all-posts',
      component: AllPostsView,
    },
    {
      path: '/my-posts',
      name: 'my-posts',
      component: MyPostsView,
      meta: { requiresAuth: true },
    },
  ],
})

router.beforeEach(async (to) => {
  const authStore = useAuthStore()

  await authStore.restoreSession()

  if (to.meta.requiresAuth && !authStore.user) {
    return { name: 'all-posts' }
  }
})
