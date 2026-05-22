import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Role } from '@/types'
import { api } from '@/services/api'

export const useAuthStore = defineStore('auth', () => {
  const savedToken = localStorage.getItem('token')
  if (savedToken) api.setToken(savedToken)

  const role        = ref<Role | null>(localStorage.getItem('role') as Role | null)
  const username    = ref<string | null>(localStorage.getItem('username'))
  const permissions = ref<string[]>(JSON.parse(localStorage.getItem('permissions') || '[]'))

  const isLoggedIn = computed(() => !!role.value)
  const isAdmin    = computed(() => role.value === 'admin')

  async function login(user: string, pass: string): Promise<void> {
    try {
      const response = await api.login(user, pass)
      const token = response.token
      const userRole = response.role

      api.setToken(token)
      role.value = userRole
      username.value = user
      permissions.value = response.permissions || []

      localStorage.setItem('token', token)
      localStorage.setItem('role', userRole)
      localStorage.setItem('username', user)
      localStorage.setItem('permissions', JSON.stringify(permissions.value))
    } catch (error) {
      throw new Error((error as Error).message || '登录失败，请检查用户名和密码')
    }
  }

  async function logout(): Promise<void> {
    try {
      await api.logout()
    } catch {
      // Ignore error on logout
    } finally {
      api.clearToken()
      role.value = null
      username.value = null
      permissions.value = []
      localStorage.removeItem('token')
      localStorage.removeItem('role')
      localStorage.removeItem('username')
      localStorage.removeItem('permissions')
    }
  }

  function restoreToken(): void {
    const token = localStorage.getItem('token')
    if (token) {
      api.setToken(token)
    }
  }

  function hasPermission(moduleName: string): boolean {
    return isAdmin.value || permissions.value.includes(moduleName)
  }

  /**
   * 从 /auth/me 拉取最新 username / role / permissions,同步到 store + localStorage。
   * 用于:admin 改员工权限后侧边栏自动反映新权限;用户修改个人资料后顶栏即时刷新。
   */
  async function refreshPermissions(): Promise<void> {
    if (!isLoggedIn.value) return
    try {
      const me = await api.getCurrentUser()
      if (me?.role) {
        role.value = me.role
        localStorage.setItem('role', me.role)
      }
      if (me?.username) {
        username.value = me.username
        localStorage.setItem('username', me.username)
      }
      const perms: string[] = me?.permissions ?? []
      // admin 端 /auth/me 不返回 permissions,这种情况保持原值不动
      if (me?.role === 'staff') {
        permissions.value = perms
        localStorage.setItem('permissions', JSON.stringify(perms))
      }
    } catch {
      // token 过期或网络错误 → 忽略,不强制踢出
    }
  }

  /** 本地直接同步资料(不再发请求)。给个人资料表单保存后用。 */
  function setProfile(updates: { username?: string }): void {
    if (updates.username) {
      username.value = updates.username
      localStorage.setItem('username', updates.username)
    }
  }

  return { role, username, permissions, isLoggedIn, isAdmin, login, logout, restoreToken, hasPermission, refreshPermissions, setProfile }
})
