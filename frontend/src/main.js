import './index.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import dayjs from 'dayjs'
import { FrappeUI, setConfig, frappeRequest, pageMetaPlugin } from 'frappe-ui'

import App from './App.vue'
import router from './router'

setConfig('resourceFetcher', frappeRequest)

const app = createApp(App)
app.use(createPinia())
app.use(FrappeUI)
app.use(router)
app.use(pageMetaPlugin)
app.provide('$dayjs', dayjs)
app.config.globalProperties.$dayjs = dayjs
app.mount('#app')
