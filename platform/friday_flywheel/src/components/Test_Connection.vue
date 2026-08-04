<script setup>
import {get,post} from '@/utils/request.js'
import {message} from "ant-design-vue";
const testConnection = async () => {
  try {
    const { data } = await post('/test_post');
    message.success('连接成功');
    console.log(data);
  } catch (error) {
    message.error(`连接失败: ${error.message}`);
  }
}

</script>

<template>
  <a-button @click="testConnection">测试连接</a-button>
</template>

<style scoped>

</style>