<script setup lang="ts">
import { storeToRefs } from 'pinia'

import AppHeader from '@/components/AppHeader.vue'
import PostsFilters from '@/components/PostsFilters.vue'
import { usePostStore } from '@/store/post.store'

const postStore = usePostStore()
const { total } = storeToRefs(postStore)
</script>

<template>
  <main class="page-shell">
    <AppHeader />
    <PostsFilters :posts-count="total" />
    <RouterView />
  </main>
</template>
