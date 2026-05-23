/* 未读通知数量管理 */

import { ref } from 'vue'
import { api } from '@/services/api'

export const unreadCount = ref(0)

export async function refreshUnread(): Promise<void> {
  try {
    const response = await api.getUnreadCount()
    unreadCount.value = Number(response?.unread_count ?? 0)
  } catch {
    
  }
}
