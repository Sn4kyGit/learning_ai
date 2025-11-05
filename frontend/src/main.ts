import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import { setupI18n } from './i18n'
import App from './App.vue'
import './assets/styles/main.css'

const app = createApp(App)
const i18n = setupI18n()

app.use(createPinia())
app.use(router)
app.use(i18n)

app.mount('#app')