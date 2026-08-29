import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'

import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'

import Root from './Root.vue'
import router from './router'
import './style.css'

// 管理后台黑主题：与对话平台一致的深色基底
document.documentElement.classList.add('dark')

const app = createApp(Root)
app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: zhCn })
app.mount('#app')
