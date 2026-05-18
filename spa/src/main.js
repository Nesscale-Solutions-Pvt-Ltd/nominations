import { createApp } from 'vue'
import {
  FrappeUI,
  Button,
  FormControl,
  ErrorMessage,
  Dialog,
  Badge,
  FeatherIcon,
  Avatar,
  Spinner,
} from 'frappe-ui'
import App from './App.vue'
import router from './router.js'
import './style.css'

const app = createApp(App)
app.use(FrappeUI)
app.use(router)

const globals = { Button, FormControl, ErrorMessage, Dialog, Badge, FeatherIcon, Avatar, Spinner }
for (const k in globals) app.component(k, globals[k])

app.mount('#app')
