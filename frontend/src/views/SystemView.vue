<template>
  <div class="fade-in">
    <PageHeader title="系统管理" subtitle="员工账号管理与模块权限配置（仅管理员）">
      <template #actions><AppBadge label="仅管理员" color="red" size="md" /></template>
    </PageHeader>
    <TabBar :tabs="tabs" :active="activeTab" @change="activeTab = $event" />

    <div style="margin-top:16px">
      <!-- 员工管理 -->
      <template v-if="activeTab === 'employees'">
        <div :class="['grid-emp', { 'grid-emp-full': !showForm }]">
          <AppCard title="员工列表">
            <template #extra><AppBtn size="sm" icon="plus" @click="showForm = !showForm">新增员工</AppBtn></template>
            <DataTable :columns="empCols" :data="(empList as Record<string,unknown>[])" :pagination="true" :page-size="5" />
          </AppCard>
          <AppCard v-if="showForm" title="新增员工">
            <form class="emp-form" @submit.prevent="addEmployee">
              <div v-for="f in formFields" :key="f.key" class="field">
                <label class="flabel">{{ f.label }}</label>
                <input v-model="newEmp[f.key]" :type="f.type || 'text'" :placeholder="f.ph" required class="finput" />
              </div>
              <div style="display:flex;gap:8px">
                <AppBtn variant="primary" style="flex:1">确认新增</AppBtn>
                <AppBtn variant="ghost" style="flex:1" @click="showForm=false">取消</AppBtn>
              </div>
            </form>
          </AppCard>
        </div>
      </template>

      <!-- 权限分配 -->
      <template v-else-if="activeTab === 'permissions'">
        <div class="grid-perm">
          <AppCard title="选择员工" :subtitle="`共 ${empList.length} 人`">
            <div class="emp-list">
              <button v-for="emp in pagedEmpList" :key="emp.id" class="emp-item" :class="{ selected: selectedEmp?.id === emp.id }" @click="selectedEmp = emp">
                <div class="emp-avatar">{{ emp.username[0] }}</div>
                <div><div class="emp-name">{{ emp.username }}</div><div class="emp-email">{{ emp.email }}</div></div>
              </button>
            </div>
            <Pagination v-if="empList.length > empPickerPageSize" :page="empPickerPage" :total="empList.length" :page-size="empPickerPageSize" @update:page="empPickerPage = $event" />
          </AppCard>
          <AppCard :title="selectedEmp ? `${selectedEmp.username} 的模块权限` : '请选择员工'" :subtitle="selectedEmp ? `共 ${selectedEmp.permissions.length} 个模块已开启` : ''">
            <div v-if="!selectedEmp" class="empty-hint">← 请从左侧选择一个员工</div>
            <div v-else class="perm-list">
              <div v-for="mod in modules" :key="mod.module_key" class="perm-item" :class="{ active: selectedEmp!.permissions.includes(mod.module_key) }">
                <div class="perm-info">
                  <div class="perm-name">{{ mod.module_name }}</div>
                  <div class="perm-desc">{{ mod.description || '—' }}</div>
                </div>
                <button class="toggle" :class="{ on: selectedEmp!.permissions.includes(mod.module_key) }" @click="togglePerm(selectedEmp!.id, mod.module_key)">
                  <span class="toggle-dot" />
                </button>
              </div>
            </div>
          </AppCard>
        </div>
      </template>

      <!-- 权限日志 -->
      <template v-else>
        <AppCard title="权限操作日志" :subtitle="`所有权限变更记录 · 共 ${filteredLogRows.length} 条`">
          <DataTable :columns="logCols" :data="(filteredLogRows as Record<string,unknown>[])" :pagination="true" :page-size="20" />
        </AppCard>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, h, onMounted } from 'vue'
import PageHeader from '@/components/common/PageHeader.vue'
import AppBadge   from '@/components/common/AppBadge.vue'
import AppBtn     from '@/components/common/AppBtn.vue'
import AppCard    from '@/components/common/AppCard.vue'
import DataTable  from '@/components/common/DataTable.vue'
import Pagination from '@/components/common/Pagination.vue'
import ColumnFilter, { type ColumnFilterOption } from '@/components/common/ColumnFilter.vue'
import ColumnTextFilter from '@/components/common/ColumnTextFilter.vue'
import TabBar     from '@/components/common/TabBar.vue'
import type { TableColumn, Employee, SystemModule, PermissionLog } from '@/types'
import { api } from '@/services/api'
import { fmtDateTime } from '@/utils/constants'

const tabs = [{ id:'employees', label:'员工管理' }, { id:'permissions', label:'权限分配' }, { id:'logs', label:'权限日志' }]
const activeTab = ref('employees')

const empList = ref<Employee[]>([])
const modules = ref<SystemModule[]>([])
const permLogs = ref<PermissionLog[]>([])
const loading = ref(false)
const errorMsg = ref<string | null>(null)

const selectedEmp = ref<Employee | null>(null)
const showForm = ref(false)

// 权限分配 tab 的"选择员工"分页(8/页,与截图分页样式一致)
const empPickerPage = ref(1)
const empPickerPageSize = 6
const pagedEmpList = computed(() => {
  const start = (empPickerPage.value - 1) * empPickerPageSize
  return empList.value.slice(start, start + empPickerPageSize)
})
const newEmp = ref<{ username: string; email: string; password: string }>({ username:'', email:'', password:'' })
const formFields: { key: 'username' | 'email' | 'password'; label: string; type?: string; ph: string }[] = [
  { key:'username', label:'用户名', ph:'请输入用户名' },
  { key:'email',    label:'邮箱',   ph:'请输入邮箱' },
  { key:'password', label:'初始密码', type:'password', ph:'请输入初始密码' },
]

// ─── 数据加载 ──────────────────────────────────────────────────────────

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
      // 选中员工的 permissions 可能已变,用最新值替换
      const refreshed = empList.value.find(e => e.id === selectedEmp.value!.id) ?? null
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

// ─── 操作 ──────────────────────────────────────────────────────────────

async function addEmployee() {
  if (!newEmp.value.username || !newEmp.value.email || !newEmp.value.password) return
  try {
    await api.createEmployee({ ...newEmp.value })
    newEmp.value = { username:'', email:'', password:'' }
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
  const emp = empList.value.find(e => e.id === empId)
  if (!emp) return
  const hasIt = emp.permissions.includes(moduleKey)
  try {
    await api.updateEmployeePermissions(empId, moduleKey, hasIt ? 'revoke' : 'grant')
    await loadAll()
  } catch (e) {
    alert(`权限切换失败:${(e as Error).message}`)
  }
}

// ─── 派生 ──────────────────────────────────────────────────────────────

const moduleNameByKey = computed(() => {
  const m: Record<string, string> = {}
  for (const mod of modules.value) m[mod.module_key] = mod.module_name
  return m
})

// 给"权限日志"表格用的展平行(已移除 remark 列)
const logRows = computed(() => permLogs.value.map(l => ({
  admin: l.admin_username,
  employee: l.target_username,
  module: moduleNameByKey.value[l.module_key] ?? l.module_key,
  action: l.action === 'grant' ? '授权' : '撤销',
  time: fmtDateTime(l.changed_at),
})))

// ─── 权限日志表头过滤 ─────────────────────────────────────────────────
// admin/employee:文本子串匹配(支持拼音段、英文段);其他三列:多选 checkbox
const logFilters = ref<{ admin: string; employee: string; module: string[]; action: string[]; time: string[] }>({
  admin: '',
  employee: '',
  module: [],
  action: [],
  time: [],
})

const logModuleOptions = computed<ColumnFilterOption[]>(() => {
  const set = new Set<string>()
  for (const r of logRows.value) set.add(r.module as string)
  return Array.from(set).sort().map(v => ({ label: v, value: v }))
})
const logActionOptions: ColumnFilterOption[] = [
  { label: '授权', value: '授权' },
  { label: '撤销', value: '撤销' },
]
const logTimeOptions = computed<ColumnFilterOption[]>(() => {
  // 用日期前缀(YYYY-MM-DD)做筛选项,label 显示 MM-DD
  const set = new Set<string>()
  for (const r of logRows.value) {
    const t = ((r.time as string) || '').slice(0, 10)
    if (t) set.add(t)
  }
  return Array.from(set).sort().reverse().map(v => ({ label: v.slice(5), value: v }))
})

const filteredLogRows = computed(() => {
  const f = logFilters.value
  const adminQ    = f.admin.trim().toLowerCase()
  const employeeQ = f.employee.trim().toLowerCase()
  return logRows.value.filter(r => {
    if (adminQ    && !((r.admin    as string) || '').toLowerCase().includes(adminQ))    return false
    if (employeeQ && !((r.employee as string) || '').toLowerCase().includes(employeeQ)) return false
    if (f.module.length && !f.module.includes(r.module as string)) return false
    if (f.action.length && !f.action.includes(r.action as string)) return false
    if (f.time.length) {
      const date = ((r.time as string) || '').slice(0, 10)
      if (!f.time.includes(date)) return false
    }
    return true
  })
})

// ─── 表格列 ────────────────────────────────────────────────────────────

const badge = (v: string, ok: string, ng: string) =>
  h('span',{style:{display:'inline-flex',alignItems:'center',padding:'2px 9px',borderRadius:'99px',fontSize:'12px',fontWeight:700,background:v===ok?'#dcfce7':v===ng?'#fee2e2':'#f1f5f0',color:v===ok?'#15803d':v===ng?'#dc2626':'#4b5563'}},v)

const empCols: TableColumn[] = [
  { key:'username', title:'用户名', render:v=>h('span',{style:{fontWeight:700}},v) },
  { key:'email',    title:'邮箱',   render:v=>h('span',{style:{fontSize:'12px',color:'var(--text2)'}},v) },
  { key:'is_active', title:'启用',  render:(_,row)=>{
    const emp = row as unknown as Employee
    return h('label',{style:{display:'inline-flex',alignItems:'center',gap:'6px',cursor:'pointer',userSelect:'none'}},[
      h('input',{
        type:'checkbox',
        checked: emp.is_active,
        style:{width:'16px',height:'16px',cursor:'pointer',accentColor:'var(--green)'},
        onChange:()=>toggleStatus(emp),
      }),
      h('span',{style:{fontSize:'12px',fontWeight:700,color: emp.is_active?'var(--green-dark)':'var(--text3)'}}, emp.is_active?'启用':'禁用'),
    ])
  } },
  { key:'created_at', title:'创建时间', render:v=>h('span',{style:{fontSize:'12px',color:'var(--text3)'}}, fmtDateTime(v as string | null)) },
  { key:'_act',     title:'操作',   render:(_,row)=>{
    const emp = row as unknown as Employee
    return h('button',{style:{padding:'6px 12px',borderRadius:'6px',fontSize:'12px',fontWeight:700,background:'var(--green-50)',color:'var(--green-dark)',border:'none',cursor:'pointer'},onClick:()=>{ selectedEmp.value = emp; activeTab.value='permissions' }},'权限')
  } },
]
const logCols: TableColumn[] = [
  {
    key: 'admin',
    title: '操作管理员',
    render: v => h('span', { style: { fontWeight: 700, color: 'var(--green-dark)' } }, v as string),
    headerRender: () => h(ColumnTextFilter, {
      title: '操作管理员',
      modelValue: logFilters.value.admin,
      'onUpdate:modelValue': (v: string) => { logFilters.value.admin = v },
    }),
  },
  {
    key: 'employee',
    title: '被操作员工',
    headerRender: () => h(ColumnTextFilter, {
      title: '被操作员工',
      modelValue: logFilters.value.employee,
      'onUpdate:modelValue': (v: string) => { logFilters.value.employee = v },
    }),
  },
  {
    key: 'module',
    title: '涉及模块',
    headerRender: () => h(ColumnFilter, {
      title: '涉及模块',
      options: logModuleOptions.value,
      selected: logFilters.value.module,
      'onUpdate:selected': (v: string[]) => { logFilters.value.module = v },
    }),
  },
  {
    key: 'action',
    title: '操作类型',
    render: v => badge(v as string, '授权', '撤销'),
    headerRender: () => h(ColumnFilter, {
      title: '操作类型',
      options: logActionOptions,
      selected: logFilters.value.action,
      'onUpdate:selected': (v: string[]) => { logFilters.value.action = v },
    }),
  },
  {
    key: 'time',
    title: '操作时间',
    render: v => h('span', { style: { fontSize: '12px', color: 'var(--text2)' } }, v as string),
    headerRender: () => h(ColumnFilter, {
      title: '操作时间',
      options: logTimeOptions.value,
      selected: logFilters.value.time,
      'onUpdate:selected': (v: string[]) => { logFilters.value.time = v },
    }),
  },
]
</script>

<style scoped>
.grid-emp  { display:grid;grid-template-columns:1fr 320px;gap:16px; }
.grid-emp-full { grid-template-columns:1fr; }   /* 无表单时员工列表占满整行 */
.grid-perm { display:grid;grid-template-columns:260px 1fr;gap:16px; }
.emp-form  { display:flex;flex-direction:column;gap:14px; }
.field     { display:flex;flex-direction:column;gap:5px; }
.flabel    { font-size:13px;font-weight:700;color:var(--text2); }
.finput    { width:100%;padding:9px 12px;border:1.5px solid var(--border);border-radius:8px;font-size:13px;outline:none;font-family:inherit; }
.emp-list  { display:flex;flex-direction:column;gap:4px; }
.emp-item  { display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:10px;border:none;cursor:pointer;text-align:left;background:transparent;transition:background .15s;width:100%; }
.emp-item:hover   { background:var(--green-50); }
.emp-item.selected{ background:var(--green-100); }
.emp-avatar{ width:32px;height:32px;border-radius:99px;background:var(--green);display:flex;align-items:center;justify-content:center;flex-shrink:0;color:#fff;font-size:12px;font-weight:800; }
.emp-name  { font-size:13px;font-weight:700;color:var(--text1); }
.emp-email { font-size:11px;color:var(--text3); }
.empty-hint{ padding:40px;text-align:center;color:var(--text3); }
.perm-list { display:flex;flex-direction:column;gap:10px; }
.perm-item { display:flex;align-items:center;gap:14px;padding:14px 16px;border-radius:10px;background:var(--bg);border:1.5px solid var(--border);transition:all .2s; }
.perm-item.active { background:var(--green-50);border-color:var(--green-100); }
.perm-info { flex:1; }
.perm-name { font-size:14px;font-weight:700;color:var(--text1); }
.perm-desc { font-size:12px;color:var(--text3);margin-top:2px; }
.toggle    { width:44px;height:24px;border-radius:99px;border:none;cursor:pointer;background:var(--border);transition:background .2s;position:relative;flex-shrink:0; }
.toggle.on { background:var(--green); }
.toggle-dot{ position:absolute;top:3px;left:3px;width:18px;height:18px;border-radius:99px;background:#fff;transition:left .2s;box-shadow:0 1px 4px rgba(0,0,0,.2); }
.toggle.on .toggle-dot { left:23px; }
</style>
