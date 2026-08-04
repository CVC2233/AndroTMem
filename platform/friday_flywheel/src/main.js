import './assets/main.css'
import Antd from 'ant-design-vue';
import { createApp } from 'vue'
import App from './App.vue'
import 'ant-design-vue/dist/reset.css';
import router from '../public/router'
createApp(App).use(Antd).use(router).mount('#app')
