<template>
  <div class="login-page">
    <div class="deco deco-tr" />
    <div class="deco deco-bl" />

    <div class="card">
      <div class="brand">
        <div class="brand-icon">
          <AppIcon name="barChart" :size="24" color="#fff" />
        </div>
        <div>
          <div class="brand-name">电商数据分析平台</div>
          <div class="brand-sub">EComm Analytics Dashboard</div>
        </div>
      </div>

      <div class="role-tabs">
        <button
          type="button"
          class="role-tab"
          :class="{ active: role === 'admin' }"
          @click="switchRole('admin')"
        >
          <AppIcon
            name="lock"
            :size="14"
            :color="role === 'admin' ? '#2d6a4f' : 'var(--text3)'"
          />
          <span>管理员</span>
        </button>

        <button
          type="button"
          class="role-tab"
          :class="{ active: role === 'employee' }"
          @click="switchRole('employee')"
        >
          <AppIcon
            name="user"
            :size="14"
            :color="role === 'employee' ? '#2d6a4f' : 'var(--text3)'"
          />
          <span>员工</span>
        </button>
      </div>

      <div v-if="role === 'admin'" class="mode-toggle">
        <button
          type="button"
          class="mode-btn"
          :class="{ active: mode === 'login' }"
          @click="switchMode('login')"
        >
          登录
        </button>

        <button
          type="button"
          class="mode-btn"
          :class="{ active: mode === 'register' }"
          @click="switchMode('register')"
        >
          注册
        </button>
      </div>

      <template v-if="role === 'employee'">
        <h2 class="title">{{ titleText }}</h2>
        <p class="desc">{{ descText }}</p>
      </template>

      <form v-if="mode === 'login'" @submit.prevent="doLogin">
        <div class="field">
          <label class="flabel">邮箱</label>
          <div class="input-wrap" :class="{ error: !!errMsg }">
            <AppIcon name="send" :size="16" color="var(--text3)" />
            <input
              v-model="loginForm.username"
              type="email"
              placeholder="you@example.com"
              required
              class="finput"
              autocomplete="email"
            />
          </div>
        </div>

        <div class="field">
          <label class="flabel">密码</label>
          <div class="input-wrap" :class="{ error: !!errMsg }">
            <AppIcon name="lock" :size="16" color="var(--text3)" />
            <input
              v-model="loginForm.password"
              type="password"
              placeholder="••••••••"
              required
              class="finput"
              autocomplete="current-password"
            />
          </div>
        </div>

        <div v-if="errMsg" class="err-tip">
          <AppIcon name="alertCircle" :size="15" color="#dc2626" />
          <span>{{ errMsg }}</span>
        </div>

        <button type="submit" :disabled="loading" class="submit-btn">
          <span v-if="loading" class="spin loader" />
          {{ loading ? '登录中…' : '登 录' }}
        </button>

        <p v-if="role === 'employee'" class="hint">
          员工账号由管理员分配，无需注册
        </p>
      </form>

      <form v-else @submit.prevent="doRegister">
        <div class="field">
          <label class="flabel">用户名</label>
          <div class="input-wrap" :class="{ error: !!errMsg }">
            <AppIcon name="user" :size="16" color="var(--text3)" />
            <input
              v-model="regForm.username"
              placeholder="3-50 字"
              required
              minlength="3"
              maxlength="50"
              class="finput"
              autocomplete="username"
            />
          </div>
        </div>

        <div class="field">
          <label class="flabel">邮箱</label>
          <div class="input-wrap" :class="{ error: !!errMsg }">
            <AppIcon name="send" :size="16" color="var(--text3)" />
            <input
              v-model="regForm.email"
              type="email"
              placeholder="you@example.com"
              required
              class="finput"
              autocomplete="email"
            />
          </div>
        </div>

        <div class="field">
          <label class="flabel">密码</label>
          <div class="input-wrap" :class="{ error: !!errMsg }">
            <AppIcon name="lock" :size="16" color="var(--text3)" />
            <input
              v-model="regForm.password"
              type="password"
              placeholder="至少 6 位"
              required
              minlength="6"
              class="finput"
              autocomplete="new-password"
            />
          </div>
        </div>

        <div class="field">
          <label class="flabel">验证码</label>
          <div class="code-row">
            <div class="input-wrap code-input" :class="{ error: !!errMsg }">
              <AppIcon name="checkCircle" :size="16" color="var(--text3)" />
              <input
                v-model="regForm.code"
                placeholder="6 位邮箱验证码"
                required
                minlength="6"
                maxlength="6"
                pattern="\d{6}"
                inputmode="numeric"
                class="finput"
              />
            </div>

            <button
              type="button"
              class="code-btn"
              :disabled="codeBtnDisabled"
              @click="doSendCode"
            >
              {{ codeBtnLabel }}
            </button>
          </div>
        </div>

        <div v-if="errMsg" class="err-tip">
          <AppIcon name="alertCircle" :size="15" color="#dc2626" />
          <span>{{ errMsg }}</span>
        </div>

        <div v-if="okMsg" class="ok-tip">
          <AppIcon name="checkCircle" :size="15" color="#16a34a" />
          <span>{{ okMsg }}</span>
        </div>

        <button type="submit" :disabled="loading" class="submit-btn">
          <span v-if="loading" class="spin loader" />
          {{ loading ? '注册中…' : '注 册' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
/* 登录与注册页面。 */
import { computed, onBeforeUnmount, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '@/components/common/AppIcon.vue'
import { api } from '@/services/api'
import { useAuthStore } from '@/stores/authStore'

const router = useRouter()
const auth = useAuthStore()

type Role = 'admin' | 'employee'
type Mode = 'login' | 'register'

const role = ref<Role>('admin')
const mode = ref<Mode>('login')

const errMsg = ref('')
const okMsg = ref('')
const loading = ref(false)

const loginForm = ref({
  username: '',
  password: '',
})

const regForm = ref({
  username: '',
  email: '',
  password: '',
  code: '',
})

const titleText = computed(() => {
  if (role.value === 'employee') {
    return '员工登录'
  }
  return mode.value === 'login' ? '管理员登录' : '管理员注册'
})

const descText = computed(() => {
  if (role.value === 'employee') {
    return '请输入管理员分配的员工账号继续'
  }
  return mode.value === 'login'
    ? '请输入您的账号和密码继续使用'
    : '注册后即可登录，验证码将发送至填写邮箱'
})

function clearFeedback(): void {
  errMsg.value = ''
  okMsg.value = ''
}

function switchRole(nextRole: Role): void {
  if (role.value === nextRole) {
    return
  }
  role.value = nextRole
  mode.value = 'login'
  clearFeedback()
}

function switchMode(nextMode: Mode): void {
  if (mode.value === nextMode) {
    return
  }
  mode.value = nextMode
  clearFeedback()
}

async function doLogin(): Promise<void> {
  clearFeedback()
  loading.value = true

  try {
    await auth.login(loginForm.value.username, loginForm.value.password)
    router.push('/sales')
  } catch (e) {
    errMsg.value = (e as Error).message
  } finally {
    loading.value = false
  }
}

const cooldown = ref(0)
let cooldownTimer: number | null = null

const codeBtnLabel = computed(() => {
  if (cooldown.value > 0) {
    return `${cooldown.value}s 后重发`
  }
  return '发送验证码'
})

const codeBtnDisabled = computed(
  () => cooldown.value > 0 || loading.value || !regForm.value.email,
)

function startCooldown(seconds = 60): void {
  cooldown.value = seconds

  if (cooldownTimer) {
    window.clearInterval(cooldownTimer)
  }

  cooldownTimer = window.setInterval(() => {
    cooldown.value -= 1
    if (cooldown.value <= 0 && cooldownTimer) {
      window.clearInterval(cooldownTimer)
      cooldownTimer = null
    }
  }, 1000)
}

onBeforeUnmount(() => {
  if (cooldownTimer) {
    window.clearInterval(cooldownTimer)
  }
})

async function doSendCode(): Promise<void> {
  clearFeedback()

  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(regForm.value.email)) {
    errMsg.value = '邮箱格式不正确'
    return
  }

  loading.value = true

  try {
    await api.sendAdminCode(regForm.value.email)
    okMsg.value = `验证码已发送至 ${regForm.value.email}，10 分钟内有效`
    startCooldown(60)
  } catch (e) {
    errMsg.value = (e as Error).message
  } finally {
    loading.value = false
  }
}

async function doRegister(): Promise<void> {
  clearFeedback()
  loading.value = true

  try {
    await api.registerAdmin({ ...regForm.value })
    okMsg.value = '注册成功，正在登录…'
    await auth.login(regForm.value.username, regForm.value.password)
    router.push('/sales')
  } catch (e) {
    errMsg.value = (e as Error).message
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background: linear-gradient(135deg, #f0fdf4, #dcfce7 50%, #bbf7d0);
}

.deco {
  position: absolute;
  border-radius: 50%;
  pointer-events: none;
}

.deco-tr {
  top: -120px;
  right: -120px;
  width: 400px;
  height: 400px;
  background: rgba(82, 183, 136, 0.12);
}

.deco-bl {
  bottom: -80px;
  left: -80px;
  width: 300px;
  height: 300px;
  background: rgba(64, 145, 108, 0.1);
}

.card {
  position: relative;
  z-index: 1;
  width: 440px;
  max-height: 92vh;
  overflow-y: auto;
  padding: 36px 40px;
  border-radius: 24px;
  background: #fff;
  box-shadow: 0 24px 64px rgba(52, 144, 104, 0.18);
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 22px;
}

.brand-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 46px;
  height: 46px;
  border-radius: 14px;
  background: linear-gradient(135deg, #52b788, #2d6a4f);
  box-shadow: 0 4px 16px rgba(52, 183, 136, 0.35);
}

.brand-name {
  font-size: 18px;
  font-weight: 900;
  color: var(--text1);
}

.brand-sub {
  margin-top: 1px;
  font-size: 12px;
  color: var(--text3);
}

.role-tabs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-bottom: 18px;
  padding: 5px;
  border-radius: 12px;
  background: var(--bg);
}

.role-tab {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 9px 12px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--text3);
  cursor: pointer;
  font-size: 14px;
  font-weight: 700;
  transition: all 0.15s;
}

.role-tab:hover {
  color: var(--green-dark);
}

.role-tab.active {
  background: #fff;
  color: var(--green-dark);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}

.mode-toggle {
  display: flex;
  gap: 14px;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--border);
}

.mode-btn {
  margin-bottom: -1px;
  padding: 8px 4px;
  border: none;
  border-bottom: 2px solid transparent;
  background: transparent;
  color: var(--text3);
  cursor: pointer;
  font-size: 14px;
  font-weight: 700;
  transition: all 0.15s;
}

.mode-btn:hover {
  color: var(--green-dark);
}

.mode-btn.active {
  color: var(--green-dark);
  border-bottom-color: var(--green);
}

.title {
  margin-bottom: 4px;
  font-size: 20px;
  font-weight: 800;
  color: var(--text1);
}

.desc {
  margin-bottom: 20px;
  font-size: 12px;
  color: var(--text2);
}

.field {
  margin-bottom: 14px;
}

.flabel {
  display: block;
  margin-bottom: 6px;
  font-size: 13px;
  font-weight: 700;
  color: var(--text2);
}

.input-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 44px;
  padding: 0 14px;
  border: 1.5px solid var(--border);
  border-radius: 12px;
  background: #fff;
  transition: border-color 0.15s;
}

.input-wrap.error {
  border-color: #fca5a5;
}

.input-wrap:focus-within {
  border-color: var(--green);
}

.code-input {
  flex: 1;
}

.finput {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  color: var(--text1);
  font-family: inherit;
  font-size: 14px;
}

.code-row {
  display: flex;
  align-items: stretch;
  gap: 8px;
}

.code-btn {
  height: 44px;
  padding: 0 16px;
  border: 1.5px solid var(--green-100);
  border-radius: 10px;
  background: var(--green-50);
  color: var(--green-dark);
  cursor: pointer;
  font-size: 13px;
  font-weight: 800;
  white-space: nowrap;
  transition: all 0.15s;
}

.code-btn:hover:not(:disabled) {
  border-color: var(--green);
  background: var(--green-100);
}

.code-btn:disabled {
  border-color: var(--border);
  background: #f1f5f0;
  color: var(--text3);
  cursor: not-allowed;
}

.err-tip {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
  padding: 10px 14px;
  border-radius: 10px;
  background: #fee2e2;
  color: #dc2626;
  font-size: 13px;
  font-weight: 600;
}

.ok-tip {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
  padding: 10px 14px;
  border-radius: 10px;
  background: #dcfce7;
  color: #15803d;
  font-size: 13px;
  font-weight: 600;
}

.submit-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  height: 46px;
  border: none;
  border-radius: 12px;
  background: linear-gradient(135deg, #52b788, #2d6a4f);
  box-shadow: 0 4px 16px rgba(52, 183, 136, 0.35);
  color: #fff;
  cursor: pointer;
  font-size: 15px;
  font-weight: 800;
  transition: all 0.2s;
}

.submit-btn:disabled {
  background: var(--text3);
  box-shadow: none;
  cursor: not-allowed;
}

.loader {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
  border-radius: 50%;
}

.hint {
  margin-top: 14px;
  color: var(--text3);
  font-size: 12px;
  line-height: 1.6;
  text-align: center;
}
</style>
