<script setup>
import { useRouter } from 'vue-router'
// 获取 router 实例
const router = useRouter()

// 跳转方法
function goToPage(pageName) {
  router.push({ name: pageName })
}
</script>

<template>
  <div>
    <h1>HomePage</h1>
    <a-button @click="goToPage('single-agent0927')">single-agent标注</a-button>
    <a-button @click="goToPage('multi-agent0927')">multi-agent标注</a-button>
    <a-button @click="goToPage('multi-agent0927-edit')">multi-agent---编辑</a-button>
  </div>
</template>

<style scoped>

</style>