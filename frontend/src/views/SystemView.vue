<template>
  <div class="fade-in">
    <PageHeader
      title="系统管理"
      subtitle="员工账号管理与模块权限配置（仅管理员）"
    >
      <template #actions>
        <AppBadge label="仅管理员" color="red" size="md" />
      </template>
    </PageHeader>

    <TabBar
      :tabs="tabs"
      :active="activeTab"
      @change="activeTab = $event"
    />

    <div class="page-section">
      <template v-if="activeTab === 'employees'">
        <div :class="['grid-emp', { 'grid-emp-full': !showForm }]">
          <AppCard title="员工列表">
            <template #extra>
              <AppBtn size="sm" icon="plus" @click="showForm = !showForm">
                新增员工
              </AppBtn>
            </template>

            <DataTable
              :columns="empCols"
              :data="empList as Record<string, unknown>[]"
              :pagination="true"
              :page-size="5"
            />
          </AppCard>

          <AppCard v-if="showForm" title="新增员工">
            <form class="emp-form" @submit.prevent="addEmployee">
              <div
                v-for="field in formFields"
                :key="field.key"
                class="field"
              >
                <label class="flabel">{{ field.label }}</label>
                <input
                  v-model="newEmp[field.key]"
                  :type="field.type || 'text'"
                  :placeholder="field.ph"
                  required
                  class="finput"
                />
              </div>

              <div class="form-actions">
                <AppBtn variant="primary" class="form-action-btn">
                  确认新增
                </AppBtn>
                <AppBtn
                  variant="ghost"
                  class="form-action-btn"
                  @click="showForm = false"
                >
                  取消
                </AppBtn>
              </div>
            </form>
          </AppCard>
        </div>
      </template>

      <template v-else-if="activeTab === 'permissions'">
        <div class="grid-perm">
          <AppCard title="选择员工" :subtitle="`共 ${empList.length} 人`">
            <div class="emp-list">
              <button
                v-for="emp in pagedEmpList"
                :key="emp.id"
                class="emp-item"
                :class="{ selected: selectedEmp?.id === emp.id }"
                @click="selectedEmp = emp"
              >
                <div class="emp-avatar">{{ emp.username[0] }}</div>
                <div>
                  <div class="emp-name">{{ emp.username }}</div>
                  <div class="emp-email">{{ emp.email }}</div>
                </div>
              </button>
            </div>

            <Pagination
              v-if="empList.length > empPickerPageSize"
              :page="empPickerPage"
              :total="empList.length"
              :page-size="empPickerPageSize"
              @update:page="empPickerPage = $event"
            />
          </AppCard>

          <AppCard
            :title="selectedEmp ? `${selectedEmp.username} 的模块权限` : '请选择员工'"
            :subtitle="
              selectedEmp ? `共 ${selectedEmp.permissions.length} 个模块已开启` : ''
            "
          >
            <div v-if="!selectedEmp" class="empty-hint">
              ← 请从左侧选择一个员工
            </div>

            <div v-else class="perm-list">
              <div
                v-for="mod in modules"
                :key="mod.module_key"
                class="perm-item"
                :class="{ active: selectedEmp!.permissions.includes(mod.module_key) }"
              >
                <div class="perm-info">
                  <div class="perm-name">{{ mod.module_name }}</div>
                  <div class="perm-desc">{{ mod.description || '—' }}</div>
                </div>

                <button
                  class="toggle"
                  :class="{ on: selectedEmp!.permissions.includes(mod.module_key) }"
                  @click="togglePerm(selectedEmp!.id, mod.module_key)"
                >
                  <span class="toggle-dot" />
                </button>
              </div>
            </div>
          </AppCard>
        </div>
      </template>

      <template v-else>
        <AppCard
          title="权限操作日志"
          :subtitle="`所有权限变更记录 · 共 ${filteredLogRows.length} 条`"
        >
          <DataTable
            :columns="logCols"
            :data="filteredLogRows as Record<string, unknown>[]"
            :pagination="true"
            :page-size="20"
          />
        </AppCard>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
/* 系统管理页面。 */
import { computed, h, onMounted, ref } from 'vue'
import AppBadge from '@/components/common/AppBadge.vue'
import AppBtn from '@/components/common/AppBtn.vue'
import AppCard from '@/components/common/AppCard.vue'
import ColumnFilter, {
  type ColumnFilterOption,
} from '@/components/common/ColumnFilter.vue'
import ColumnTextFilter from '@/components/common/ColumnTextFilter.vue'
import DataTable from '@/components/common/DataTable.vue'
import PageHeader from '@/components/common/PageHeader.vue'
import Pagination from '@/components/common/Pagination.vue'
import TabBar from '@/components/common/TabBar.vue'
import { api } from '@/services/api'
import type {
  Employee,
  PermissionLog,
  SystemModule,
  TableColumn,
} from '@/types'
import { fmtDateTime } from '@/utils/constants'

const tabs = [
  { id: 'employees', label: '员工管理' },
  { id: 'permissions', label: '权限分配' },
  { id: 'logs', label: '权限日志' },
]

const activeTab = ref('employees')

const empList = ref<Employee[]>([])
const modules = ref<SystemModule[]>([])
const permLogs = ref<PermissionLog[]>([])
const loading = ref(false)
const errorMsg = ref<string | null>(null)

const selectedEmp = ref<Employee | null>(null)
const showForm = ref(false)

const empPickerPage = ref(1)
const empPickerPageSize = 6

const pagedEmpList = computed(() => {
  const start = (empPickerPage.value - 1) * empPickerPageSize
  return empList.value.slice(start, start + empPickerPageSize)
})

const newEmp = ref<{ username: string; email: string; password: string }>({
  username: '',
  email: '',
  password: '',
})

const formFields: {
  key: 'username' | 'email' | 'password'
  label: string
  type?: string
  ph: string
}[] = [
  { key: 'username', label: '用户名', ph: '请输入用户名' },
  { key: 'email', label: '邮箱', ph: '请输入邮箱' },
  {
    key: 'password',
    label: '初始密码',
    type: 'password',
    ph: '请输入初始密码',
  },
]

async function loadAll() {
  loading.value = true
  errorMsg.value = null

  try {
    const [empResp, modsResp, logsResp] = await Promise.all([
      api.getEmployees(1, 10000),
      api.getModules(),
      api.getPermissionLogs(1, 10000),
    ])

    empList.value = (empResp?.data ?? []) as Employee[]
    modules.value = (modsResp ?? []) as SystemModule[]
    permLogs.value = (logsResp?.data ?? []) as PermissionLog[]

    if (selectedEmp.value) {
      const refreshed =
        empList.value.find((emp) => emp.id === selectedEmp.value!.id) ?? null
      selectedEmp.value = refreshed
    }
  } catch (e) {
    errorMsg.value = (e as Error).message
    console.error('[SystemView] load failed', e)
  } finally {
    loading.value = false
  }
}

onMounted(loadAll)

async function addEmployee() {
  if (!newEmp.value.username || !newEmp.value.email || !newEmp.value.password) {
    return
  }

  try {
    await api.createEmployee({ ...newEmp.value })
    newEmp.value = { username: '', email: '', password: '' }
    showForm.value = false
    await loadAll()
  } catch (e) {
    alert(`新增员工失败:${(e as Error).message}`)
  }
}

async function toggleStatus(emp: Employee) {
  try {
    await api.updateEmployee(emp.id, { is_active: !emp.is_active })
    await loadAll()
  } catch (e) {
    alert(`切换状态失败:${(e as Error).message}`)
  }
}

async function togglePerm(empId: number, moduleKey: string) {
  const emp = empList.value.find((item) => item.id === empId)
  if (!emp) {
    return
  }

  const hasIt = emp.permissions.includes(moduleKey)

  try {
    await api.updateEmployeePermissions(
      empId,
      moduleKey,
      hasIt ? 'revoke' : 'grant',
    )
    await loadAll()
  } catch (e) {
    alert(`权限切换失败:${(e as Error).message}`)
  }
}

const moduleNameByKey = computed(() => {
  const map: Record<string, string> = {}

  for (const mod of modules.value) {
    map[mod.module_key] = mod.module_name
  }

  return map
})

const logRows = computed(() =>
  permLogs.value.map((log) => ({
    admin: log.admin_username,
    employee: log.target_username,
    module: moduleNameByKey.value[log.module_key] ?? log.module_key,
    action: log.action === 'grant' ? '授权' : '撤销',
    time: fmtDateTime(log.changed_at),
  })),
)

const logFilters = ref<{
  admin: string
  employee: string
  module: string[]
  action: string[]
  time: string[]
}>({
  admin: '',
  employee: '',
  module: [],
  action: [],
  time: [],
})

const logModuleOptions = computed<ColumnFilterOption[]>(() => {
  const values = new Set<string>()

  for (const row of logRows.value) {
    values.add(row.module as string)
  }

  return Array.from(values)
    .sort()
    .map((value) => ({ label: value, value }))
})

const logActionOptions: ColumnFilterOption[] = [
  { label: '授权', value: '授权' },
  { label: '撤销', value: '撤销' },
]

const logTimeOptions = computed<ColumnFilterOption[]>(() => {
  const values = new Set<string>()

  for (const row of logRows.value) {
    const date = ((row.time as string) || '').slice(0, 10)
    if (date) {
      values.add(date)
    }
  }

  return Array.from(values)
    .sort()
    .reverse()
    .map((value) => ({
      label: value.slice(5),
      value,
    }))
})

const filteredLogRows = computed(() => {
  const filters = logFilters.value
  const adminQuery = filters.admin.trim().toLowerCase()
  const employeeQuery = filters.employee.trim().toLowerCase()

  return logRows.value.filter((row) => {
    if (
      adminQuery &&
      !(((row.admin as string) || '').toLowerCase().includes(adminQuery))
    ) {
      return false
    }

    if (
      employeeQuery &&
      !(((row.employee as string) || '').toLowerCase().includes(employeeQuery))
    ) {
      return false
    }

    if (filters.module.length && !filters.module.includes(row.module as string)) {
      return false
    }

    if (filters.action.length && !filters.action.includes(row.action as string)) {
      return false
    }

    if (filters.time.length) {
      const date = ((row.time as string) || '').slice(0, 10)
      if (!filters.time.includes(date)) {
        return false
      }
    }

    return true
  })
})

const badge = (value: string, ok: string, ng: string) =>
  h(
    'span',
    {
      style: {
        display: 'inline-flex',
        alignItems: 'center',
        padding: '2px 9px',
        borderRadius: '99px',
        fontSize: '12px',
        fontWeight: 700,
        background:
          value === ok ? '#dcfce7' : value === ng ? '#fee2e2' : '#f1f5f0',
        color: value === ok ? '#15803d' : value === ng ? '#dc2626' : '#4b5563',
      },
    },
    value,
  )

const empCols: TableColumn[] = [
  {
    key: 'username',
    title: '用户名',
    render: (value) =>
      h(
        'span',
        {
          style: { fontWeight: 700 },
        },
        String(value),
      ),
  },
  {
    key: 'email',
    title: '邮箱',
    render: (value) =>
      h(
        'span',
        {
          style: { fontSize: '12px', color: 'var(--text2)' },
        },
        String(value),
      ),
  },
  {
    key: 'is_active',
    title: '启用',
    render: (_, row) => {
      const emp = row as unknown as Employee

      return h(
        'label',
        {
          style: {
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            cursor: 'pointer',
            userSelect: 'none',
          },
        },
        [
          h('input', {
            type: 'checkbox',
            checked: emp.is_active,
            style: {
              width: '16px',
              height: '16px',
              cursor: 'pointer',
              accentColor: 'var(--green)',
            },
            onChange: () => toggleStatus(emp),
          }),
          h(
            'span',
            {
              style: {
                fontSize: '12px',
                fontWeight: 700,
                color: emp.is_active ? 'var(--green-dark)' : 'var(--text3)',
              },
            },
            emp.is_active ? '启用' : '禁用',
          ),
        ],
      )
    },
  },
  {
    key: 'created_at',
    title: '创建时间',
    render: (value) =>
      h(
        'span',
        {
          style: { fontSize: '12px', color: 'var(--text3)' },
        },
        fmtDateTime(value as string | null),
      ),
  },
  {
    key: '_act',
    title: '操作',
    render: (_, row) => {
      const emp = row as unknown as Employee

      return h(
        'button',
        {
          style: {
            padding: '6px 12px',
            borderRadius: '6px',
            fontSize: '12px',
            fontWeight: 700,
            background: 'var(--green-50)',
            color: 'var(--green-dark)',
            border: 'none',
            cursor: 'pointer',
          },
          onClick: () => {
            selectedEmp.value = emp
            activeTab.value = 'permissions'
          },
        },
        '权限',
      )
    },
  },
]

const logCols: TableColumn[] = [
  {
    key: 'admin',
    title: '操作管理员',
    render: (value) =>
      h(
        'span',
        {
          style: {
            fontWeight: 700,
            color: 'var(--green-dark)',
          },
        },
        value as string,
      ),
    headerRender: () =>
      h(ColumnTextFilter, {
        title: '操作管理员',
        modelValue: logFilters.value.admin,
        'onUpdate:modelValue': (value: string) => {
          logFilters.value.admin = value
        },
      }),
  },
  {
    key: 'employee',
    title: '被操作员工',
    headerRender: () =>
      h(ColumnTextFilter, {
        title: '被操作员工',
        modelValue: logFilters.value.employee,
        'onUpdate:modelValue': (value: string) => {
          logFilters.value.employee = value
        },
      }),
  },
  {
    key: 'module',
    title: '涉及模块',
    headerRender: () =>
      h(ColumnFilter, {
        title: '涉及模块',
        options: logModuleOptions.value,
        selected: logFilters.value.module,
        'onUpdate:selected': (value: string[]) => {
          logFilters.value.module = value
        },
      }),
  },
  {
    key: 'action',
    title: '操作类型',
    render: (value) => badge(value as string, '授权', '撤销'),
    headerRender: () =>
      h(ColumnFilter, {
        title: '操作类型',
        options: logActionOptions,
        selected: logFilters.value.action,
        'onUpdate:selected': (value: string[]) => {
          logFilters.value.action = value
        },
      }),
  },
  {
    key: 'time',
    title: '操作时间',
    render: (value) =>
      h(
        'span',
        {
          style: { fontSize: '12px', color: 'var(--text2)' },
        },
        value as string,
      ),
    headerRender: () =>
      h(ColumnFilter, {
        title: '操作时间',
        options: logTimeOptions.value,
        selected: logFilters.value.time,
        'onUpdate:selected': (value: string[]) => {
          logFilters.value.time = value
        },
      }),
  },
]
</script>

<style scoped>
.page-section {
  margin-top: 16px;
}

.grid-emp {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 16px;
}

.grid-emp-full {
  grid-template-columns: 1fr;
}

.grid-perm {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 16px;
}

.emp-form {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.flabel {
  font-size: 13px;
  font-weight: 700;
  color: var(--text2);
}

.finput {
  width: 100%;
  padding: 9px 12px;
  border: 1.5px solid var(--border);
  border-radius: 8px;
  font-size: 13px;
  outline: none;
  font-family: inherit;
}

.form-actions {
  display: flex;
  gap: 8px;
}

.form-action-btn {
  flex: 1;
}

.emp-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.emp-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 12px;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  text-align: left;
  background: transparent;
  transition: background 0.15s;
}

.emp-item:hover {
  background: var(--green-50);
}

.emp-item.selected {
  background: var(--green-100);
}

.emp-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: 99px;
  background: var(--green);
  color: #fff;
  font-size: 12px;
  font-weight: 800;
}

.emp-name {
  font-size: 13px;
  font-weight: 700;
  color: var(--text1);
}

.emp-email {
  font-size: 11px;
  color: var(--text3);
}

.empty-hint {
  padding: 40px;
  text-align: center;
  color: var(--text3);
}

.perm-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.perm-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  border: 1.5px solid var(--border);
  border-radius: 10px;
  background: var(--bg);
  transition: all 0.2s;
}

.perm-item.active {
  background: var(--green-50);
  border-color: var(--green-100);
}

.perm-info {
  flex: 1;
}

.perm-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--text1);
}

.perm-desc {
  margin-top: 2px;
  font-size: 12px;
  color: var(--text3);
}

.toggle {
  position: relative;
  flex-shrink: 0;
  width: 44px;
  height: 24px;
  border: none;
  border-radius: 99px;
  cursor: pointer;
  background: var(--border);
  transition: background 0.2s;
}

.toggle.on {
  background: var(--green);
}

.toggle-dot {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 18px;
  height: 18px;
  border-radius: 99px;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.2);
  transition: left 0.2s;
}

.toggle.on .toggle-dot {
  left: 23px;
}
</style>
