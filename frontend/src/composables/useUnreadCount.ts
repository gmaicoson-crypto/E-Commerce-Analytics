/**
 * 全局未读通知数 —— 模块级单例 ref,共享给 TopBar / Sidebar / NotificationsView。
 *
 * 在 MainLayout 里挂载 SSE 订阅 + 初次拉取(参见 layouts/MainLayout.vue);
 * 其他组件只 import { unreadCount, refreshUnread } 用即可。
 */
import { ref } from 'vue'
import { api } from '@/services/api'

export const unreadCount = ref(0)

export async function refreshUnread(): Promise<void> {
  try {
    const response = await api.getUnreadCount()
    unreadCount.value = Number(response?.unread_count ?? 0)
  } catch {
    // 静默忽略(非 admin 会 401/403,正常)
  }
}
