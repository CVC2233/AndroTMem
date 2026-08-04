import { createRouter, createWebHistory,createWebHashHistory } from 'vue-router'

const routes = [
    {
        path: '/',       // 当访问根路径 / 时
        name: 'Home',
        component: ()=>import( '@/views/HomePage.vue'),
    },
    {
        path: '/multi-agent0927',
        name: 'multi-agent0927',
        component: () => import('@/views/MultiAgents0927.vue'),
    },
    {
        path: '/multi-agent0927-edit',
        name: 'multi-agent0927-edit',
        component: () => import('@/views/MultiAgents0927Edit.vue'),
    },
    {
        path: '/single-agent0927',
        name: 'single-agent0927',
        component: () => import('@/views/SingleAgent0927.vue'),
    },
]

const router = createRouter({
    history: createWebHashHistory(), // <-- 修改这里,默认的 history 模式在 file:// 协议下是无法工作的（刷新页面或直接访问子路径会 404）。你需要将它改为 hash 模式
    routes
})

export default router
