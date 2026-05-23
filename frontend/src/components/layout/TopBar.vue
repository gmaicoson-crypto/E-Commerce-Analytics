<template>
  <header class="topbar">
    <HeadlineMarquee />
    <HotProductsTicker v-if="auth.isAdmin" />
    <div class="spacer" />
    <span class="date">{{ dateStr }}</span>
    <div v-if="auth.isAdmin" class="bell-wrap">
      <button class="icon-btn" title="通知中心" @click="router.push('/notifications')">
        <AppIcon name="bell" :size="18" color="var(--text2)" />
        <span v-if="unreadCount > 0" class="bell-dot" />
      </button>
    </div>
    <button class="user-info" title="点击查看资料 / 修改密码" @click="openProfile">
      <div class="u-avatar"><AppIcon name="user" :size="14" color="#fff" /></div>
      <span class="u-name">{{ auth.username ?? '—' }}</span>
      <AppBadge :label="roleLabel" :color="auth.isAdmin ? 'green' : 'blue'" />
    </button>
    <Teleport to="body">
      <div v-if="showModal" class="modal-mask" @click.self="closeModal">
        <div class="modal-card">
          <div class="modal-head">
            <h3>个人资料</h3>
            <button class="modal-x" @click="closeModal">×</button>
          </div>
          <section class="form-block">
            <div class="block-title">基本信息</div>
            <div class="profile-row">
              <span class="prow-label">角色</span>
              <AppBadge :label="roleLabel" :color="auth.isAdmin ? 'green' : 'blue'" />
            </div>
            <div class="form-row">
              <label>用户名</label>
              <input v-model="profile.username" class="finput" placeholder="2-50 字符" />
            </div>
            <div class="form-row">
              <label>邮箱</label>
              <input v-model="profile.email" type="email" class="finput" placeholder="user@example.com" />
            </div>
            <div class="btn-row">
              <button class="btn-primary" :disabled="savingProfile" @click="saveProfile">
                {{ savingProfile ? '保存中…' : '保存资料' }}
              </button>
            </div>
            <div v-if="profileMsg" class="msg" :class="profileOk ? 'ok' : 'err'">{{ profileMsg }}</div>
          </section>
          <section class="form-block">
            <div class="block-title">修改密码</div>
            <div class="form-row">
              <label>原密码</label>
              <input v-model="pwd.old_password" type="password" class="finput" placeholder="当前密码" />
            </div>
            <div class="form-row">
              <label>新密码</label>
              <input v-model="pwd.new_password" type="password" class="finput" placeholder="至少 4 位" />
            </div>
            <div class="form-row">
              <label>确认</label>
              <input v-model="pwd.confirm" type="password" class="finput" placeholder="再次输入新密码" />
            </div>
            <div class="btn-row">
              <button class="btn-primary" :disabled="savingPwd" @click="savePassword">
                {{ savingPwd ? '保存中…' : '修改密码' }}
              </button>
            </div>
            <div v-if="pwdMsg" class="msg" :class="pwdOk ? 'ok' : 'err'">{{ pwdMsg }}</div>
          </section>
        </div>
      </div>
    </Teleport>
  </header>
</template>

<script setup lang="ts">
/* 顶部导航与个人资料弹窗 */
import { computed, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/services/api'
import { unreadCount } from '@/composables/useUnreadCount'
import AppIcon from '@/components/common/AppIcon.vue'
import AppBadge from '@/components/common/AppBadge.vue'
import HeadlineMarquee from '@/components/layout/HeadlineMarquee.vue'
import HotProductsTicker from '@/components/layout/HotProductsTicker.vue'
import { useAuthStore } from '@/stores/authStore'

const auth = useAuthStore()
const router = useRouter()
const now = new Date()
const dateStr = computed(() => `${now.getFullYear()}年${now.getMonth() + 1}月${now.getDate()}日`)
const roleLabel = computed(() => (auth.isAdmin ? '管理员' : '员工'))

const showModal = ref(false)
const profile = reactive({ username: '', email: '' })
const pwd = reactive({ old_password: '', new_password: '', confirm: '' })
const savingProfile = ref(false)
const savingPwd = ref(false)
const profileMsg = ref('')
const profileOk = ref(false)
const pwdMsg = ref('')
const pwdOk = ref(false)

async function openProfile() {
  showModal.value = true
  profileMsg.value = ''
  pwdMsg.value = ''
  pwd.old_password = ''
  pwd.new_password = ''
  pwd.confirm = ''
  
  try {
    const me = await api.getCurrentUser()
    profile.username = me?.username ?? auth.username ?? ''
    profile.email = me?.email ?? ''
  } catch {
    profile.username = auth.username ?? ''
    profile.email = ''
  }
}

function closeModal() {
  showModal.value = false
}

async function saveProfile() {
  if (!profile.username || !profile.email) {
    profileMsg.value = '用户名和邮箱不能为空'
    profileOk.value = false
    return
  }
  savingProfile.value = true
  profileMsg.value = ''
  try {
    const updated = await api.updateProfile({ username: profile.username, email: profile.email })
    auth.setProfile({ username: updated?.username ?? profile.username })
    profileOk.value = true
    profileMsg.value = '资料已保存'
  } catch (e) {
    profileOk.value = false
    profileMsg.value = (e as Error).message
  } finally {
    savingProfile.value = false
  }
}

async function savePassword() {
  if (!pwd.old_password || !pwd.new_password) {
    pwdMsg.value = '请填写原密码和新密码'
    pwdOk.value = false
    return
  }
  if (pwd.new_password !== pwd.confirm) {
    pwdMsg.value = '两次输入的新密码不一致'
    pwdOk.value = false
    return
  }
  savingPwd.value = true
  pwdMsg.value = ''
  try {
    await api.changePassword({ old_password: pwd.old_password, new_password: pwd.new_password })
    pwdOk.value = true
    pwdMsg.value = '密码已修改,下次登录请使用新密码'
    pwd.old_password = ''
    pwd.new_password = ''
    pwd.confirm = ''
  } catch (e) {
    pwdOk.value = false
    pwdMsg.value = (e as Error).message
  } finally {
    savingPwd.value = false
  }
}
</script>

<style scoped>
.topbar {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  gap: 14px;
  height: var(--header-h);
  padding: 0 28px;
  background: var(--card);
  border-bottom: 1px solid var(--border);
}

.spacer {
  flex: 1;
}

.date {
  font-size: 13px;
  font-weight: 600;
  color: var(--text2);
}

.bell-wrap {
  position: relative;
}

.icon-btn {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 10px;
  background: var(--bg);
  cursor: pointer;
  transition: background 0.15s;
}

.icon-btn:hover {
  background: var(--green-50);
}

.bell-dot {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 8px;
  height: 8px;
  border: 2px solid var(--card);
  border-radius: 99px;
  background: #ef4444;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border: none;
  border-radius: 10px;
  background: var(--bg);
  cursor: pointer;
  transition: background 0.15s;
}

.user-info:hover {
  background: var(--green-50);
}

.u-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 99px;
  background: var(--green);
}

.u-name {
  max-width: 120px;
  overflow: hidden;
  font-size: 13px;
  font-weight: 700;
  color: var(--text1);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.modal-mask {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
  background: rgba(17, 24, 39, 0.45);
}

.modal-card {
  display: flex;
  flex-direction: column;
  width: 440px;
  max-width: 92vw;
  max-height: 90vh;
  overflow-y: auto;
  border-radius: 14px;
  background: #fff;
  box-shadow: 0 14px 48px rgba(0, 0, 0, 0.18);
}

.modal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
}

.modal-head h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 800;
  color: var(--green-dark);
}

.modal-x {
  border: none;
  background: none;
  color: var(--text3);
  cursor: pointer;
  font-size: 24px;
  line-height: 1;
}

.modal-x:hover {
  color: var(--text1);
}

.form-block {
  padding: 14px 20px;
  border-bottom: 1px solid var(--border);
}

.form-block:last-child {
  border-bottom: none;
}

.block-title {
  margin-bottom: 10px;
  font-size: 12px;
  font-weight: 700;
  color: var(--text2);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.profile-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
  padding: 6px 0;
}

.prow-label {
  font-size: 13px;
  font-weight: 700;
  color: var(--text2);
}

.form-row {
  display: grid;
  grid-template-columns: 64px 1fr;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.form-row label {
  font-size: 13px;
  font-weight: 700;
  color: var(--text2);
}

.finput {
  width: 100%;
  padding: 7px 10px;
  border: 1.5px solid var(--border);
  border-radius: 7px;
  outline: none;
  font-family: inherit;
  font-size: 13px;
}

.finput:focus {
  border-color: var(--green);
}

.btn-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 6px;
}

.btn-primary {
  padding: 7px 16px;
  border: none;
  border-radius: 7px;
  background: var(--green);
  color: #fff;
  cursor: pointer;
  font-size: 13px;
  font-weight: 700;
}

.btn-primary:hover:not(:disabled) {
  background: var(--green-dark);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.msg {
  margin-top: 8px;
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 12px;
}

.msg.ok {
  background: #dcfce7;
  color: #15803d;
}

.msg.err {
  background: #fee2e2;
  color: #dc2626;
}
</style>
