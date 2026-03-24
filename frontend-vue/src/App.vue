<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

<template>
  <RouterView v-slot="{ Component }">
    <KeepAlive include="Dashboard">
      <component :is="Component" />
    </KeepAlive>
  </RouterView>
</template>

<style scoped>
/* 可以在这里放一些全局或局部的基础样式，目前为空即可 */
</style>