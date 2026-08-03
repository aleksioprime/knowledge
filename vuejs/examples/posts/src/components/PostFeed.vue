<script setup lang="ts">
import { storeToRefs } from 'pinia'

import PostsLoader from '@/components/PostsLoader.vue'
import PostsList from '@/components/PostsList.vue'
import StatePanel from '@/components/StatePanel.vue'
import { usePostStore, type PostScope } from '@/store/post.store'

const props = defineProps<{
  scope: PostScope
}>()

const postStore = usePostStore()
const { posts, isLoading, error, hasMore, pageState } = storeToRefs(postStore)

postStore.openFeed(props.scope)
</script>

<template>
  <StatePanel v-if="pageState" :type="pageState" :message="error" @retry="postStore.loadPosts" />

  <template v-else>
    <PostsList :posts="posts" />
    <PostsLoader
      :loading="isLoading"
      :has-more="hasMore"
      :error="error"
      @load="postStore.loadPosts"
      @retry="postStore.loadPosts"
    />
  </template>
</template>
