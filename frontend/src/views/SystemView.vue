<template>
  <div class="fade-in">
    <PageHeader title="系统管理" subtitle="员工账号管理与模块权限配置（仅管理员）">
      <template #actions><AppBadge label="仅管理员" color="red" size="md" /></template>
    </PageHeader>
    <TabBar :tabs="tabs" :active="activeTab" @change="activeTab = $event" />

    <div style="margin-top:16px">
      <!-- 员工管理 -->
      <template v-if="activeTab === 'employees'">
        <div class="grid-emp">
          <AppCard title="员工列表">
            <template #extra><AppBtn size="sm" icon="plus" @click="showForm = !showForm">新增员工</AppBtn></template>
            <DataTable :columns="empCols" :data="(empList as Record<string,unknown>[])" />
          </AppCard>
          <AppCard :title="showForm ? '新增员工' : '员工统计'">
            <form v-if="showForm" class="emp-form" @submit.prevent="addEmployee">
              <div v-for="f in formFields" :key="f.key" class="field">
                <label class="flabel">{{ f.label }}</label>
                <input v-model="newEmp[f.key]" :type="f.type || 'text'" :placeholder="f.ph" required class="finput" />
              </div>
              <div style="display:flex;gap:8px">
                <AppBtn variant="primary" style="flex:1">确认新增</AppBtn>
                <AppBtn variant="ghost" style="flex:1" @click="showForm=false">取消</AppBtn>
              </div>
            </form>
            <div v-else class="stats-list">
              <div v-for="s in empStats" :key="s.label" class="stat-row">
                <span class="stat-label">{{ s.label }}</span>
                <span class="stat-value" :style="{ color: s.color }">{{ s.value }}</span>
              </div>
            </div>
          </AppCard>
        </div>
      </template>

      <!-- 权限分配 -->
      <template v-else-if="activeTab === 'permissions'">
        <div class="grid-perm">
          <AppCard title="选择员工">
            <div class="emp-list">
              <button v-for="emp in empList" :key="emp.id" class="emp-item" :class="{ selected: selectedEmp?.id === emp.id }" @click="selectedEmp = emp">
                <div class="emp-avatar">{{ emp.username[0] }}</div>
                <div><div class="emp-name">{{ emp.username }}</div><div class="emp-email">{{ emp.email }}</div></div>
              </button>
            </div>
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
        <AppCard title="权限操作日志" subtitle="所有权限变更记录">
          <DataTable :columns="logCols" :data="(logRows as Record<string,unknown>[])" />
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

const empStats = computed(() => [
  { label:'全部员工', value: empList.value.length, color:'var(--green)' },
  { label:'已启用',   value: empList.value.filter(e => e.is_active).length, color:'#16a34a' },
  { label:'已禁用',   value: empList.value.filter(e => !e.is_active).length, color:'#dc2626' },
])

const moduleNameByKey = computed(() => {
  const m: Record<string, string> = {}
  for (const mod of modules.value) m[mod.module_key] = mod.module_name
  return m
})

// 给"权限日志"表格用的展平行
const logRows = computed(() => permLogs.value.map(l => ({
  admin: l.admin_username,
  employee: l.target_username,
  module: moduleNameByKey.value[l.module_key] ?? l.module_key,
  action: l.action === 'grant' ? '授权' : '撤销',
  time: fmtDateTime(l.changed_at),
  remark: l.remark ?? '—',
})))

// ─── 表格列 ────────────────────────────────────────────────────────────

const badge = (v: string, ok: string, ng: string) =>
  h('span',{style:{display:'inline-flex',alignItems:'center',padding:'2px 9px',borderRadius:'99px',fontSize:'12px',fontWeight:700,background:v===ok?'#dcfce7':v===ng?'#fee2e2':'#f1f5f0',color:v===ok?'#15803d':v===ng?'#dc2626':'#4b5563'}},v)

const empCols: TableColumn[] = [
  { key:'username', title:'用户名', render:v=>h('span',{style:{fontWeight:700}},v) },
  { key:'email',    title:'邮箱',   render:v=>h('span',{style:{fontSize:'12px',color:'var(--text2)'}},v) },
  { key:'is_active',title:'状态',   render:v=>badge(v ? '启用' : '禁用','启用','禁用') },
  { key:'created_at', title:'创建时间', render:v=>h('span',{style:{fontSize:'12px',color:'var(--text3)'}}, fmtDateTime(v as string | null)) },
  { key:'_act',     title:'操作',   render:(_,row)=>{
    const emp = row as unknown as Employee
    return h('div',{style:{display:'flex',gap:'6px'}},[
      h('button',{style:{padding:'6px 12px',borderRadius:'6px',fontSize:'12px',fontWeight:700,background: emp.is_active?'#fee2e2':'var(--green-50)',color: emp.is_active?'#dc2626':'var(--green-dark)',border:'none',cursor:'pointer'},onClick:()=>toggleStatus(emp)}, emp.is_active?'禁用':'启用'),
      h('button',{style:{padding:'6px 12px',borderRadius:'6px',fontSize:'12px',fontWeight:700,background:'var(--green-50)',color:'var(--green-dark)',border:'none',cursor:'pointer'},onClick:()=>{ selectedEmp.value = emp; activeTab.value='permissions' }},'权限'),
    ])
  } },
]
const logCols: TableColumn[] = [
  { key:'admin',    title:'操作管理员', render:v=>h('span',{style:{fontWeight:700,color:'var(--green-dark)'}}, v as string) },
  { key:'employee', title:'被操作员工' },
  { key:'module',   title:'涉及模块' },
  { key:'action',   title:'操作类型', render:v=>badge(v as string,'授权','撤销') },
  { key:'time',     title:'操作时间', render:v=>h('span',{style:{fontSize:'12px',color:'var(--text2)'}}, v as string) },
  { key:'remark',   title:'备注', render:v=>h('span',{style:{fontSize:'12px',color:'var(--text3)'}}, v as string) },
]
</script>

<style scoped>
.grid-emp  { display:grid;grid-template-columns:1fr 320px;gap:16px; }
.grid-perm { display:grid;grid-template-columns:260px 1fr;gap:16px; }
.emp-form  { display:flex;flex-direction:column;gap:14px; }
.field     { display:flex;flex-direction:column;gap:5px; }
.flabel    { font-size:13px;font-weight:700;color:var(--text2); }
.finput    { width:100%;padding:9px 12px;border:1.5px solid var(--border);border-radius:8px;font-size:13px;outline:none;font-family:inherit; }
.stats-list{ display:flex;flex-direction:column;gap:12px; }
.stat-row  { display:flex;justify-content:space-between;align-items:center;padding:12px 0;border-bottom:1px solid var(--border); }
.stat-label{ font-size:14px;color:var(--text2);font-weight:600; }
.stat-value{ font-size:22px;font-weight:900; }
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
