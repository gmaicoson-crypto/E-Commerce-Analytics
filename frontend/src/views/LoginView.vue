<template>
  <div class="login-page">
    <div class="deco deco-tr" /><div class="deco deco-bl" />
    <div class="card">
      <div class="brand">
        <div class="brand-icon"><AppIcon name="barChart" :size="24" color="#fff" /></div>
        <div>
          <div class="brand-name">电商数据分析平台</div>
          <div class="brand-sub">EComm Analytics Dashboard</div>
        </div>
      </div>
      <h2 class="title">欢迎登录</h2>
      <p class="desc">请输入您的账号和密码继续使用</p>
      <form @submit.prevent="submit">
        <div class="field">
          <label class="flabel">用户名</label>
          <div class="input-wrap" :class="{ error: !!errMsg }">
            <AppIcon name="user" :size="16" color="var(--text3)" />
            <input v-model="username" placeholder="admin 或 staff" required class="finput" />
          </div>
        </div>
        <div class="field">
          <label class="flabel">密码</label>
          <div class="input-wrap" :class="{ error: !!errMsg }">
            <AppIcon name="lock" :size="16" color="var(--text3)" />
            <input v-model="password" type="password" placeholder="••••••••" required class="finput" />
          </div>
        </div>
        <div v-if="errMsg" class="err-tip">
          <AppIcon name="alertCircle" :size="15" color="#dc2626" /><span>{{ errMsg }}</span>
        </div>
        <button type="submit" :disabled="loading" class="submit-btn">
          <span v-if="loading" class="spin loader" />
          {{ loading ? '登录中…' : '登 录' }}
        </button>
      </form>
      <div class="demo-box">
        <p class="demo-title">🧪 演示账号</p>
        <p>管理员：admin / admin123</p>
        <p>员工：staff / staff123</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/authStore'
import AppIcon from '@/components/common/AppIcon.vue'

const router   = useRouter()
const auth     = useAuthStore()
const username = ref('')
const password = ref('')
const errMsg   = ref('')
const loading  = ref(false)

async function submit() {
  errMsg.value  = ''
  loading.value = true
  try {
    await auth.login(username.value, password.value)
    router.push('/sales')
  } catch (e) {
    errMsg.value = (e as Error).message
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page { width:100vw;height:100vh;display:flex;align-items:center;justify-content:center;overflow:hidden;background:linear-gradient(135deg,#f0fdf4,#dcfce7 50%,#bbf7d0); }
.deco { position:absolute;border-radius:50%;pointer-events:none; }
.deco-tr { top:-120px;right:-120px;width:400px;height:400px;background:rgba(82,183,136,.12); }
.deco-bl { bottom:-80px;left:-80px;width:300px;height:300px;background:rgba(64,145,108,.1); }
.card { width:420px;background:#fff;border-radius:24px;box-shadow:0 24px 64px rgba(52,144,104,.18);padding:44px 40px;position:relative;z-index:1; }
.brand { display:flex;align-items:center;gap:12px;margin-bottom:36px; }
.brand-icon { width:46px;height:46px;border-radius:14px;background:linear-gradient(135deg,#52b788,#2d6a4f);display:flex;align-items:center;justify-content:center;box-shadow:0 4px 16px rgba(52,183,136,.35); }
.brand-name { font-size:18px;font-weight:900;color:var(--text1); }
.brand-sub  { font-size:12px;color:var(--text3);margin-top:1px; }
.title { font-size:22px;font-weight:800;color:var(--text1);margin-bottom:6px; }
.desc  { font-size:13px;color:var(--text2);margin-bottom:28px; }
.field { margin-bottom:16px; }
.flabel { font-size:13px;font-weight:700;color:var(--text2);display:block;margin-bottom:6px; }
.input-wrap { display:flex;align-items:center;gap:10px;border:1.5px solid var(--border);border-radius:12px;padding:0 14px;height:46px;transition:border-color .15s; }
.input-wrap.error { border-color:#fca5a5; }
.input-wrap:focus-within { border-color:var(--green); }
.finput { flex:1;border:none;outline:none;font-size:14px;color:var(--text1);background:transparent; }
.err-tip { display:flex;align-items:center;gap:8px;background:#fee2e2;border-radius:10px;padding:10px 14px;margin-bottom:18px;font-size:13px;color:#dc2626;font-weight:600; }
.submit-btn { width:100%;height:48px;border-radius:12px;background:linear-gradient(135deg,#52b788,#2d6a4f);color:#fff;font-size:15px;font-weight:800;border:none;cursor:pointer;box-shadow:0 4px 16px rgba(52,183,136,.35);transition:all .2s;display:flex;align-items:center;justify-content:center;gap:8px; }
.submit-btn:disabled { background:var(--text3);box-shadow:none;cursor:not-allowed; }
.loader { display:inline-block;width:16px;height:16px;border:2px solid rgba(255,255,255,.4);border-top-color:#fff;border-radius:50%; }
.demo-box { margin-top:24px;padding:14px 16px;background:var(--green-50);border-radius:12px;border:1px solid var(--green-100);font-size:12px;color:var(--text2); }
.demo-title { font-weight:700;margin-bottom:6px; }
</style>
