/* 登录态与当前用户状态管理 */

import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import type { Role } from '@/types'
import { api } from '@/services/api'

export const useAuthStore = defineStore('auth', () => {
  const savedToken = localStorage.getItem('token')
  if (savedToken) {
    api.setToken(savedToken)
  }

  const role = ref<Role | null>(localStorage.getItem('role') as Role | null)
  const username = ref<string | null>(localStorage.getItem('username'))
  const permissions = ref<string[]>(JSON.parse(localStorage.getItem('permissions') || '[]'))

  const isLoggedIn = computed(() => !!role.value)
  const isAdmin = computed(() => role.value === 'admin')

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

  
  async function refreshPermissions(): Promise<void> {
    if (!isLoggedIn.value) {
      return
    }

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

      
      if (me?.role === 'staff') {
        permissions.value = perms
        localStorage.setItem('permissions', JSON.stringify(perms))
      }
    } catch {
      
    }
  }

  
  function setProfile(updates: { username?: string }): void {
    if (updates.username) {
      username.value = updates.username
      localStorage.setItem('username', updates.username)
    }
  }

  return {
    role,
    username,
    permissions,
    isLoggedIn,
    isAdmin,
    login,
    logout,
    restoreToken,
    hasPermission,
    refreshPermissions,
    setProfile,
  }
})
