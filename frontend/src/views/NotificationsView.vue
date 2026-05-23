<template>
  <div class="fade-in">
    <PageHeader
      title="通知中心"
      subtitle="系统预警与重要通知（仅管理员）"
    >
      <template #actions>
        <AppBadge
          v-if="unread > 0"
          :label="`${unread} 条未读`"
          color="red"
          size="md"
        />
        <AppBtn
          size="sm"
          variant="ghost"
          icon="checkCircle"
          @click="markAllRead"
        >
          全部标为已读
        </AppBtn>
      </template>
    </PageHeader>

    <div class="filter-row">
      <button
        v-for="t in types"
        :key="t"
        class="type-btn"
        :class="{ active: filter === t }"
        @click="filter = t"
      >
        {{ t }}
        <span
          v-if="unreadCount(t) > 0"
          class="count"
          :class="{ active: filter === t }"
        >
          {{ unreadCount(t) }}
        </span>
      </button>
      <div v-if="filtered.length > 0" class="select-row">
        <label class="select-all">
          <input
            type="checkbox"
            :checked="allSelected"
            :indeterminate.prop="someSelected && !allSelected"
            @change="toggleSelectAll"
          />
          <span>全选当前</span>
        </label>
        <span v-if="selectedCount > 0" class="select-info">已选 {{ selectedCount }} 条</span>
        <button
          v-if="selectedCount > 0"
          class="bulk-del-btn"
          @click="deleteSelected"
        >
          删除选中 ({{ selectedCount }})
        </button>
      </div>
    </div>
    <div class="notif-list">
      <div v-if="loading" class="empty-card">
        加载中...
      </div>
      <div v-else-if="filtered.length === 0" class="empty-card">
        暂无{{ filter === '全部' ? '' : filter }}通知
      </div>
      <div
        v-for="n in filtered"
        :key="n.id"
        class="notif-item"
        :class="{ selected: selected.has(n.id) }"
        :style="{ borderLeftColor: n.read ? 'var(--border)' : TC[n.type], opacity: n.read ? 0.75 : 1 }"
      >
        <label class="notif-check">
          <input
            type="checkbox"
            :checked="selected.has(n.id)"
            @change="toggleSelect(n.id)"
          />
        </label>
        <div class="notif-icon" :style="{ background: TB[n.type] }">
          <AppIcon :name="TI[n.type]" :size="18" :color="TC[n.type]" />
        </div>
        <div class="notif-body">
          <div class="notif-meta">
            <span
              class="notif-badge"
              :style="{ background: TB[n.type], color: TC[n.type] }"
            >
              {{ n.type }}
            </span>
            <span v-if="!n.read" class="unread-dot" />
            <span class="notif-time">{{ n.time }}</span>
          </div>
          <div class="notif-title">{{ n.title }}</div>
          <div class="notif-content">{{ n.content }}</div>
        </div>
        <div class="notif-actions">
          <button
            v-if="!n.read"
            class="read-btn"
            @click="markRead(n.id)"
          >
            标为已读
          </button>
          <button class="del-btn" title="删除" @click="deleteOne(n.id)">
            <AppIcon name="close" :size="14" color="currentColor" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/* 通知中心页面。 */
import { computed, onMounted, ref } from 'vue'
import AppBadge from '@/components/common/AppBadge.vue'
import AppBtn from '@/components/common/AppBtn.vue'
import AppIcon from '@/components/common/AppIcon.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import { refreshUnread } from '@/composables/useUnreadCount'
import { useDebouncedReload } from '@/composables/useEventStream'
import { api } from '@/services/api'
import type { Notification, NotificationType } from '@/types'
import { NOTIF_TYPE_ZH, fmtDateTime } from '@/utils/constants'

const TC: Record<string, string> = {
  '库存预警': '#ca8a04',
  '大额退款': '#dc2626',
  '异常订单': '#ea580c',
  '销售额波动': '#2563eb',
}
const TB: Record<string, string> = {
  '库存预警': '#fef9c3',
  '大额退款': '#fee2e2',
  '异常订单': '#ffedd5',
  '销售额波动': '#dbeafe',
}
const TI: Record<string, string> = {
  '库存预警': 'package',
  '大额退款': 'finance',
  '异常订单': 'alertCircle',
  '销售额波动': 'sales',
}

const notifications = ref<Notification[]>([])
const loading = ref(true)

const types = ['全部', '库存预警', '大额退款', '异常订单', '销售额波动']
const filter = ref('全部')
const unread = computed(() => notifications.value.filter(n => !n.read).length)
const filtered = computed(() =>
  filter.value === '全部'
    ? notifications.value
    : notifications.value.filter(n => n.type === filter.value)
)

function unreadCount(t: string) {
  return t === '全部'
    ? unread.value
    : notifications.value.filter(n => n.type === t && !n.read).length
}

const selected = ref<Set<number>>(new Set())
const selectedCount = computed(() => {
  return filtered.value.reduce((acc, n) => acc + (selected.value.has(n.id) ? 1 : 0), 0)
})
const someSelected = computed(() => selectedCount.value > 0)
const allSelected = computed(() =>
  filtered.value.length > 0 && filtered.value.every(n => selected.value.has(n.id))
)

function toggleSelect(id: number) {
  const next = new Set(selected.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selected.value = next
}

function toggleSelectAll() {
  const next = new Set(selected.value)
  if (allSelected.value) {
    filtered.value.forEach(n => next.delete(n.id))
  } else {
    filtered.value.forEach(n => next.add(n.id))
  }
  selected.value = next
}

async function deleteOne(id: number) {
  if (!confirm('确认删除该通知?')) return
  const prev = notifications.value
  notifications.value = notifications.value.filter(n => n.id !== id)
  if (selected.value.has(id)) {
    const next = new Set(selected.value)
    next.delete(id)
    selected.value = next
  }
  try {
    await api.deleteNotification(id)
    refreshUnread()
  } catch (e) {
    console.error('[NotificationsView] delete failed', e)
    notifications.value = prev
  }
}

async function deleteSelected() {
  const ids = filtered.value.filter(n => selected.value.has(n.id)).map(n => n.id)
  if (ids.length === 0) return
  if (!confirm(`确认删除选中的 ${ids.length} 条通知?`)) return
  const prev = notifications.value
  const idSet = new Set(ids)
  notifications.value = notifications.value.filter(n => !idSet.has(n.id))
  const nextSel = new Set(selected.value)
  ids.forEach(i => nextSel.delete(i))
  selected.value = nextSel
  try {
    await api.deleteBatchNotifications(ids)
    refreshUnread()
  } catch (e) {
    console.error('[NotificationsView] batch delete failed', e)
    notifications.value = prev
  }
}

async function load() {
  loading.value = true
  try {
    const resp = await api.getNotifications(1, 10000)
    const list: Array<{
      id: number
      type: string
      title: string
      content: string
      is_read: boolean
      created_at: string | null
    }> = resp?.data ?? []
    notifications.value = list.map(n => ({
      id: n.id,
      type: (NOTIF_TYPE_ZH[n.type] ?? n.type) as NotificationType,
      title: n.title,
      content: n.content,
      read: n.is_read,
      time: fmtDateTime(n.created_at),
    }))
  } catch (e) {
    console.error('[NotificationsView] load failed', e)
  } finally {
    loading.value = false
  }
}

async function markRead(id: number) {
  const n = notifications.value.find(n => n.id === id)
  if (!n || n.read) return
  n.read = true
  try {
    await api.markNotificationAsRead(id)
    refreshUnread()
  } catch (e) {
    console.error('[NotificationsView] markRead failed', e)
    n.read = false
  }
}

async function markAllRead() {
  const unreadIds = notifications.value.filter(n => !n.read).map(n => n.id)
  if (unreadIds.length === 0) return
  const prev = notifications.value.map(n => ({ ...n }))
  notifications.value.forEach(n => (n.read = true))
  try {
    await api.markBatchAsRead(unreadIds)
    refreshUnread()
  } catch (e) {
    console.error('[NotificationsView] markAllRead failed', e)
    notifications.value = prev
  }
}

onMounted(load)
useDebouncedReload(['notification'], load)
</script>

<style scoped>
.filter-row {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
  align-items: center;
}

.type-btn {
  padding: 7px 16px;
  border-radius: 99px;
  font-size: 13px;
  font-weight: 700;
  border: 1.5px solid var(--border);
  background: white;
  color: var(--text2);
  cursor: pointer;
  transition: all 0.15s;
  display: flex;
  align-items: center;
  gap: 6px;
}

.type-btn.active {
  background: var(--green);
  border-color: var(--green);
  color: #fff;
}

.count {
  width: 18px;
  height: 18px;
  border-radius: 99px;
  background: #ef4444;
  color: #fff;
  font-size: 10px;
  font-weight: 900;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.count.active {
  background: rgba(255, 255, 255, 0.35);
}

.select-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-left: auto;
}

.select-all {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text2);
  cursor: pointer;
  user-select: none;
}

.select-all input {
  width: 15px;
  height: 15px;
  cursor: pointer;
  accent-color: var(--green);
}

.select-info {
  font-size: 12px;
  color: var(--text3);
  font-weight: 600;
}

.bulk-del-btn {
  padding: 7px 14px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 700;
  background: #fee2e2;
  color: #dc2626;
  border: none;
  cursor: pointer;
  transition: all 0.15s;
}

.bulk-del-btn:hover {
  background: #fecaca;
}

.notif-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.empty-card {
  padding: 60px;
  text-align: center;
  color: var(--text3);
  background: var(--card);
  border-radius: var(--r);
  box-shadow: var(--shadow);
}

.notif-item {
  background: var(--card);
  border-radius: var(--r);
  box-shadow: var(--shadow);
  padding: 16px 20px;
  display: flex;
  gap: 14px;
  align-items: flex-start;
  border-left: 4px solid var(--border);
  transition: all 0.2s;
}

.notif-item.selected {
  background: var(--green-50);
}

.notif-check {
  display: flex;
  align-items: center;
  padding-top: 4px;
  cursor: pointer;
}

.notif-check input {
  width: 16px;
  height: 16px;
  cursor: pointer;
  accent-color: var(--green);
}

.notif-icon {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.notif-body {
  flex: 1;
  min-width: 0;
}

.notif-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 5px;
}

.notif-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 9px;
  border-radius: 99px;
  font-size: 12px;
  font-weight: 700;
}

.unread-dot {
  width: 7px;
  height: 7px;
  border-radius: 99px;
  background: #ef4444;
  display: inline-block;
}

.notif-time {
  font-size: 12px;
  color: var(--text3);
  margin-left: auto;
}

.notif-title {
  font-size: 14px;
  font-weight: 800;
  color: var(--text1);
  margin-bottom: 4px;
}

.notif-content {
  font-size: 13px;
  color: var(--text2);
  line-height: 1.6;
}

.notif-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.read-btn {
  padding: 6px 12px;
  border-radius: 7px;
  font-size: 12px;
  font-weight: 700;
  background: var(--green-50);
  color: var(--green-dark);
  border: none;
  cursor: pointer;
  white-space: nowrap;
}

.read-btn:hover {
  background: var(--green-100);
}

.del-btn {
  width: 28px;
  height: 28px;
  border-radius: 7px;
  border: none;
  background: transparent;
  color: var(--text3);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s;
}

.del-btn:hover {
  background: #fee2e2;
  color: #dc2626;
}
</style>
