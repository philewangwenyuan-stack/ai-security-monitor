import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import AlertDetail from '../views/AlertDetail.vue'
import AdminConfig from '../views/AdminConfig.vue'

const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes: [
        { path: '/', name: 'dashboard', component: Dashboard },
        { path: '/alert/:id', name: 'alert-detail', component: AlertDetail },
        { path: '/admin', name: 'admin', component: AdminConfig }
    ]
})

export default router