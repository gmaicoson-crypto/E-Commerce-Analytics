/**
 * 数据模拟生成器前端 · 单文件
 * 与同源 FastAPI(8001)对话,所有路径都是相对的 /api/*
 */

const $ = (s, root = document) => root.querySelector(s)
const $$ = (s, root = document) => Array.from(root.querySelectorAll(s))

// 34 个省级行政区 —— 与后端 data_factory.PROVINCES、前端 chinaMap.PROVINCE_FULL_NAME 严格对齐
const PROVINCES = [
  // 直辖市
  '北京', '上海', '天津', '重庆',
  // 省
  '河北', '山西', '辽宁', '吉林', '黑龙江',
  '江苏', '浙江', '安徽', '福建', '江西',
  '山东', '河南', '湖北', '湖南', '广东',
  '海南', '四川', '贵州', '云南', '陕西',
  '甘肃', '青海', '台湾',
  // 自治区
  '内蒙古', '广西', '西藏', '宁夏', '新疆',
  // 特别行政区
  '香港', '澳门',
]
const CATEGORIES = ['服装', '电子', '食品', '家居', '美妆']
const ORDER_STATUSES = ['pending', 'paid', 'shipped', 'completed', 'cancelled']

// 订单状态机:与 backend data_factory.ALLOWED_ORDER_TRANSITIONS 严格对齐
// 编辑订单时 status 下拉只展示当前状态 + 可达后继
const ALLOWED_ORDER_TRANSITIONS = {
  pending:   ['paid', 'cancelled'],
  paid:      ['shipped'],
  shipped:   ['completed'],
  completed: [],
  cancelled: [],
}
const FINANCE_TYPES = ['income', 'expense']
const FINANCE_CATEGORIES = ['sales_income', 'logistics_cost', 'ad_cost']
const NOTIF_TYPES = ['stock_alert', 'order_alert', 'sales_alert']

// ─── 实体 schema ─────────────────────────────────────────────────────

const ENTITIES = {
  customer: {
    label: '客户',
    cols: [
      { key: 'id',            label: 'ID' },
      { key: 'username',      label: '用户名' },
      { key: 'gender',        label: '性别' },
      { key: 'age_group',     label: '年龄段' },
      { key: 'province',      label: '省份' },
      { key: 'customer_type', label: '类型' },
      { key: 'registered_at', label: '注册时间', fmt: fmtDate },
    ],
    filters: [
      { key: 'gender',        label: '性别',   options: ['male', 'female'] },
      { key: 'age_group',     label: '年龄段', options: ['18-24', '25-34', '35-44', '45+'] },
      { key: 'province',      label: '省份',   options: PROVINCES },
      { key: 'customer_type', label: '类型',   options: ['new', 'returning'] },
    ],
    createFields: [
      { key: 'count',         label: '数量',   type: 'number', default: 1, hint: '1=单条;>1=批量(最多 500)' },
      { key: 'gender',        label: '性别',   type: 'select', options: ['', 'male', 'female'], hint: '空=随机' },
      { key: 'age_group',     label: '年龄段', type: 'select', options: ['', '18-24', '25-34', '35-44', '45+'] },
      { key: 'province',      label: '省份',   type: 'select', options: ['', ...PROVINCES] },
      { key: 'customer_type', label: '类型',   type: 'select', options: ['', 'new', 'returning'] },
    ],
    supportsBulk: true,
    supportsBulkDelete: true,
    editFields: [
      { key: 'username',      label: '用户名', type: 'text' },
      { key: 'gender',        label: '性别',   type: 'select', options: ['male', 'female'] },
      { key: 'age_group',     label: '年龄段', type: 'select', options: ['18-24', '25-34', '35-44', '45+'] },
      { key: 'province',      label: '省份',   type: 'select', options: PROVINCES },
      { key: 'customer_type', label: '类型',   type: 'select', options: ['new', 'returning'] },
    ],
  },
  product: {
    label: '商品',
    cols: [
      { key: 'id',                  label: 'ID' },
      { key: 'product_name',        label: '名称' },
      { key: 'category',            label: '品类' },
      { key: 'price',               label: '价格', fmt: fmtMoney },
      { key: 'cost',                label: '成本', fmt: fmtMoney },
      { key: 'stock',               label: '库存' },
      { key: 'low_stock_threshold', label: '预警阈值' },
      { key: 'status',              label: '状态' },
    ],
    filters: [
      { key: 'category', label: '品类', options: CATEGORIES },
      { key: 'status',   label: '状态', options: ['on_sale', 'off_sale'] },
    ],
    createFields: [
      { key: 'count',    label: '数量', type: 'number', default: 1, hint: '1=单条;>1=批量(最多 500)' },
      { key: 'category', label: '品类', type: 'select', options: ['', ...CATEGORIES], hint: '空=随机' },
      { key: 'status',   label: '状态', type: 'select', options: ['on_sale', 'off_sale'] },
      { key: 'price',    label: '价格', type: 'number', hint: '空=10-500 随机' },
      { key: 'cost',     label: '成本', type: 'number', hint: '空=5-250 随机' },
      { key: 'stock',    label: '库存', type: 'number', hint: '空=50-500 随机' },
    ],
    supportsBulk: true,
    supportsBulkDelete: true,
    editFields: [
      { key: 'product_name',        label: '名称',     type: 'text' },
      { key: 'category',            label: '品类',     type: 'select', options: CATEGORIES },
      { key: 'status',              label: '状态',     type: 'select', options: ['on_sale', 'off_sale'] },
      { key: 'price',               label: '价格',     type: 'number' },
      { key: 'cost',                label: '成本',     type: 'number' },
      { key: 'stock',               label: '库存',     type: 'number' },
      { key: 'low_stock_threshold', label: '预警阈值', type: 'number' },
    ],
  },
  order: {
    label: '订单',
    cols: [
      { key: 'id',           label: 'ID' },
      { key: 'order_no',     label: '订单号' },
      { key: 'customer',     label: '客户' },
      { key: 'total_amount', label: '金额', fmt: fmtMoney },
      { key: 'status',       label: '状态' },
      { key: 'created_at',   label: '创建时间', fmt: fmtDate },
    ],
    filters: [
      { key: 'status', label: '状态', options: ORDER_STATUSES },
    ],
    createFields: [
      { key: 'status',      label: '状态',    type: 'select', options: ['', ...ORDER_STATUSES], hint: '空=按权重(新规则下推荐 pending)' },
      { key: 'customer_id', label: '客户 ID', type: 'number', hint: '空=随机' },
    ],
    supportsBulkDelete: true,
    editFields: [
      { key: 'status', label: '状态', type: 'select', options: ORDER_STATUSES, hint: '受状态机约束:pending→paid/cancelled,paid→shipped,shipped→completed' },
    ],
  },
  finance: {
    label: '财务',
    cols: [
      { key: 'id',               label: 'ID' },
      { key: 'type',             label: '类型' },
      { key: 'category',         label: '分类' },
      { key: 'amount',           label: '金额', fmt: fmtMoney },
      { key: 'related_order_id', label: '关联订单' },
      { key: 'recorded_at',      label: '入账时间', fmt: fmtDate },
    ],
    filters: [
      { key: 'type',     label: '类型', options: FINANCE_TYPES },
      { key: 'category', label: '分类', options: FINANCE_CATEGORIES },
    ],
    createFields: [
      { key: 'type',     label: '类型', type: 'select', options: ['', ...FINANCE_TYPES], hint: '空=随机' },
      { key: 'category', label: '分类', type: 'select', options: ['', ...FINANCE_CATEGORIES], hint: '空=按类型兜底' },
      { key: 'amount',   label: '金额', type: 'number', hint: '空=100-10000 随机' },
    ],
    editFields: [
      { key: 'type',     label: '类型', type: 'select', options: FINANCE_TYPES },
      { key: 'category', label: '分类', type: 'select', options: FINANCE_CATEGORIES },
      { key: 'amount',   label: '金额', type: 'number' },
    ],
  },
  notification: {
    label: '通知',
    cols: [
      { key: 'id',         label: 'ID' },
      { key: 'type',       label: '类型' },
      { key: 'title',      label: '标题' },
      { key: 'content',    label: '内容' },
      { key: 'is_read',    label: '已读', fmt: (v) => v ? '✓' : '·' },
      { key: 'created_at', label: '时间', fmt: fmtDate },
    ],
    filters: [
      { key: 'ntype',   label: '类型', options: NOTIF_TYPES },
      { key: 'is_read', label: '已读', options: ['true', 'false'] },
    ],
    createFields: [
      { key: 'ntype',   label: '类型', type: 'select', options: ['', ...NOTIF_TYPES], hint: '空=随机' },
      { key: 'title',   label: '标题', type: 'text' },
      { key: 'content', label: '内容', type: 'text' },
    ],
    editFields: [
      { key: 'is_read', label: '已读', type: 'select', options: ['true', 'false'] },
      { key: 'title',   label: '标题', type: 'text' },
      { key: 'content', label: '内容', type: 'text' },
    ],
  },
}

// ─── 格式化 helper ───────────────────────────────────────────────────

function fmtDate(v) {
  if (!v) return ''
  const d = new Date(v)
  return d.toLocaleString('zh-CN', { hour12: false })
}

function fmtMoney(v) {
  if (v === null || v === undefined) return ''
  return '¥' + Number(v).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// ─── 状态 ────────────────────────────────────────────────────────────

const state = {
  entity: 'customer',
  page: 1,
  pageSize: 10,
  filters: {},
  modal: { mode: null, row: null },
}

const logEl  = $('#log')
const statusEl = $('#status')

function log(msg, level = 'info') {
  const t = new Date().toLocaleTimeString('zh-CN', { hour12: false })
  const prefix = level === 'err' ? '✗' : level === 'ok' ? '✓' : '·'
  logEl.textContent += `[${t}] ${prefix} ${msg}\n`
  logEl.scrollTop = logEl.scrollHeight
}

function setStatus(text, cls) {
  statusEl.textContent = text
  statusEl.className = 'status ' + (cls || '')
}

// ─── API 调用 ────────────────────────────────────────────────────────

async function api(path, opts = {}) {
  const headers = opts.body ? { 'Content-Type': 'application/json' } : {}
  const r = await fetch(`/api${path}`, { headers, ...opts })
  const j = await r.json().catch(() => ({}))
  if (!r.ok) {
    const msg = (j && j.detail && j.detail.message) || j.message || `HTTP ${r.status}`
    throw new Error(msg)
  }
  return j.data
}

// ─── 计数 ───────────────────────────────────────────────────────────

async function refreshCounts() {
  try {
    const d = await api('/counts')
    $('#cnt-customers').textContent     = (d.customers ?? 0).toLocaleString()
    $('#cnt-products').textContent      = (d.products ?? 0).toLocaleString()
    $('#cnt-orders').textContent        = (d.orders ?? 0).toLocaleString()
    $('#cnt-finance').textContent       = (d.finance_records ?? 0).toLocaleString()
    $('#cnt-notifications').textContent = (d.notifications ?? 0).toLocaleString()
    setStatus('已连接', 'ok')
  } catch (e) {
    setStatus('连接失败', 'err')
  }
}

// ─── 渲染:filter / table / pagination ────────────────────────────────

function renderFilterRow() {
  const def = ENTITIES[state.entity]
  const root = $('#filter-row')
  root.innerHTML = ''
  for (const f of def.filters) {
    const sel = document.createElement('select')
    sel.dataset.filterKey = f.key
    sel.innerHTML = `<option value="">${f.label}:全部</option>` +
      f.options.map((o) => `<option value="${o}">${o}</option>`).join('')
    sel.value = state.filters[f.key] || ''
    sel.addEventListener('change', () => {
      if (sel.value) state.filters[f.key] = sel.value
      else delete state.filters[f.key]
      state.page = 1
      loadList()
    })
    root.appendChild(sel)
  }
}

function renderTable(rows) {
  const def = ENTITIES[state.entity]
  const bulk = def.supportsBulkDelete
  const checkHead = bulk ? '<th class="check-col"><input type="checkbox" id="head-check" /></th>' : ''
  $('#thead-row').innerHTML =
    checkHead +
    def.cols.map((c) => `<th>${c.label}</th>`).join('') +
    '<th class="actions">操作</th>'

  const totalCols = def.cols.length + 1 + (bulk ? 1 : 0)
  if (!rows.length) {
    $('#tbody').innerHTML =
      `<tr><td colspan="${totalCols}" class="empty">暂无数据</td></tr>`
    syncBulkDeleteBtn()
    return
  }

  $('#tbody').innerHTML = rows.map((r) => {
    const cells = def.cols.map((c) => {
      const v = r[c.key]
      const display = c.fmt ? c.fmt(v) : (v === null || v === undefined ? '' : String(v))
      return `<td>${escapeHtml(display)}</td>`
    }).join('')
    const checkCell = bulk ? `<td class="check-col"><input type="checkbox" class="row-check" data-id="${r.id}" /></td>` : ''
    return `
      <tr data-id="${r.id}">
        ${checkCell}${cells}
        <td class="actions">
          <button class="btn ghost small" data-act="edit"  data-id="${r.id}">编辑</button>
          <button class="btn danger small" data-act="del" data-id="${r.id}">删除</button>
        </td>
      </tr>
    `
  }).join('')

  $$('button[data-act="edit"]', $('#tbody')).forEach((b) => {
    b.addEventListener('click', () => {
      const row = rows.find((x) => String(x.id) === b.dataset.id)
      openModal('edit', row)
    })
  })
  $$('button[data-act="del"]', $('#tbody')).forEach((b) => {
    b.addEventListener('click', () => deleteRow(b.dataset.id))
  })

  // 行 checkbox 监听
  $$('input.row-check', $('#tbody')).forEach((cb) => {
    cb.addEventListener('change', syncBulkDeleteBtn)
  })
  // 全选 checkbox
  const headCheck = $('#head-check')
  if (headCheck) {
    headCheck.addEventListener('change', () => {
      $$('input.row-check', $('#tbody')).forEach((cb) => (cb.checked = headCheck.checked))
      syncBulkDeleteBtn()
    })
  }
  syncBulkDeleteBtn()
}

function getSelectedIds() {
  return $$('input.row-check:checked', $('#tbody')).map((cb) => Number(cb.dataset.id))
}

function syncBulkDeleteBtn() {
  const btn = $('#btn-bulk-del')
  if (!btn) return
  const def = ENTITIES[state.entity]
  if (!def.supportsBulkDelete) {
    btn.style.display = 'none'
    btn.disabled = true
    return
  }
  btn.style.display = ''
  const ids = getSelectedIds()
  btn.textContent = `删除选中 (${ids.length})`
  btn.disabled = ids.length === 0
  // 同步表头全选状态(部分/全部)
  const head = $('#head-check')
  if (head) {
    const all = $$('input.row-check', $('#tbody'))
    if (all.length === 0) {
      head.checked = false
      head.indeterminate = false
    } else if (ids.length === all.length) {
      head.checked = true
      head.indeterminate = false
    } else {
      head.checked = false
      head.indeterminate = ids.length > 0
    }
  }
}

async function bulkDeleteSelected() {
  const def = ENTITIES[state.entity]
  if (!def.supportsBulkDelete) return
  const ids = getSelectedIds()
  if (ids.length === 0) return
  if (!confirm(`确认删除选中的 ${ids.length} 条 ${def.label}?`)) return
  try {
    const result = await api(`/${state.entity}/bulk-delete`, {
      method: 'POST',
      body: JSON.stringify({ ids }),
    })
    const okCount = result.deleted?.length ?? 0
    const skipCount = result.skipped?.length ?? 0
    if (okCount > 0) {
      log(`批量删除 ${def.label}:成功 ${okCount} 条${skipCount ? `,跳过 ${skipCount} 条` : ''}`, 'ok')
    }
    if (skipCount > 0) {
      const reasons = result.skipped.map((s) => `#${s.id}(${s.reason})`).join(', ')
      log(`跳过原因:${reasons}`, 'err')
    }
    loadList()
    refreshCounts()
  } catch (e) {
    log(`批量删除失败:${e.message}`, 'err')
  }
}

function renderPagination(pg) {
  const wrap = $('#pagination')
  if (!pg || !pg.total_pages) { wrap.innerHTML = ''; return }
  wrap.innerHTML = `
    <span class="pg-info">共 ${pg.total} 条 · ${pg.page}/${pg.total_pages} 页</span>
    <button class="btn ghost small" id="pg-prev" ${pg.page <= 1 ? 'disabled' : ''}>上一页</button>
    <input class="pg-input" id="pg-input" type="number" min="1" max="${pg.total_pages}" value="${pg.page}" />
    <button class="btn ghost small" id="pg-next" ${pg.page >= pg.total_pages ? 'disabled' : ''}>下一页</button>
  `
  $('#pg-prev').addEventListener('click', () => { state.page = Math.max(1, state.page - 1); loadList() })
  $('#pg-next').addEventListener('click', () => { state.page = Math.min(pg.total_pages, state.page + 1); loadList() })
  $('#pg-input').addEventListener('change', (e) => {
    const v = parseInt(e.target.value, 10)
    if (v && v >= 1 && v <= pg.total_pages) { state.page = v; loadList() }
  })
}

// ─── 数据流 ──────────────────────────────────────────────────────────

async function loadList() {
  const qs = new URLSearchParams({
    page: state.page, page_size: state.pageSize,
    ...state.filters,
  }).toString()
  try {
    const d = await api(`/${state.entity}/list?${qs}`)
    renderTable(d.data || [])
    renderPagination(d.pagination)
  } catch (e) {
    log(`加载${ENTITIES[state.entity].label}列表失败:${e.message}`, 'err')
    renderTable([])
    renderPagination(null)
  }
}

async function deleteRow(id) {
  if (!confirm(`确认删除 ${ENTITIES[state.entity].label} #${id}?`)) return
  try {
    await api(`/${state.entity}/${id}`, { method: 'DELETE' })
    log(`删除 ${ENTITIES[state.entity].label} #${id} 成功`, 'ok')
    loadList()
    refreshCounts()
  } catch (e) {
    log(`删除 ${ENTITIES[state.entity].label} #${id} 失败:${e.message}`, 'err')
  }
}

// ─── Modal ───────────────────────────────────────────────────────────

function openModal(mode, row) {
  state.modal = { mode, row }
  const def = ENTITIES[state.entity]
  const fields = mode === 'create' ? def.createFields : def.editFields
  $('#modal-title').textContent = `${mode === 'create' ? '新增' : '编辑'} ${def.label}${row ? ' #' + row.id : ''}`
  $('#modal-body').innerHTML = fields.map((f) => {
    const id = `f-${f.key}`
    let val = row ? (row[f.key] === null || row[f.key] === undefined ? '' : row[f.key]) : ''
    if (!row && (val === '' || val === undefined) && f.default !== undefined) val = f.default
    if (f.type === 'select') {
      // 状态机过滤:编辑订单的 status 字段时,只展示当前状态 + 可达后继
      let options = f.options
      if (mode === 'edit' && state.entity === 'order' && f.key === 'status' && row) {
        const cur = row.status
        const reachable = ALLOWED_ORDER_TRANSITIONS[cur] ?? []
        options = [cur, ...reachable]
      }
      const opts = options.map((o) => {
        const lbl = o === '' ? '(随机/默认)' : o
        const selected = String(val) === String(o) ? ' selected' : ''
        return `<option value="${o}"${selected}>${lbl}</option>`
      }).join('')
      return `
        <div class="form-row">
          <label for="${id}">${f.label}</label>
          <select id="${id}" data-field="${f.key}">${opts}</select>
          ${f.hint ? `<span class="form-hint">${f.hint}</span>` : ''}
        </div>
      `
    }
    const inputType = f.type === 'number' ? 'number' : 'text'
    return `
      <div class="form-row">
        <label for="${id}">${f.label}</label>
        <input id="${id}" type="${inputType}" value="${escapeHtml(String(val))}" data-field="${f.key}" />
        ${f.hint ? `<span class="form-hint">${f.hint}</span>` : ''}
      </div>
    `
  }).join('')
  $('#modal-mask').classList.add('open')
}

function closeModal() {
  state.modal = { mode: null, row: null }
  $('#modal-mask').classList.remove('open')
}

function collectModalBody() {
  const body = {}
  $$('#modal-body [data-field]').forEach((el) => {
    const k = el.dataset.field
    let v = el.value.trim()
    if (v === '') return  // 跳过空值
    if (el.type === 'number') {
      const n = Number(v)
      if (!Number.isFinite(n)) return
      body[k] = n
    } else if (v === 'true') body[k] = true
    else if (v === 'false') body[k] = false
    else body[k] = v
  })
  return body
}

async function submitModal() {
  const { mode, row } = state.modal
  if (!mode) return
  const body = collectModalBody()
  const def = ENTITIES[state.entity]
  try {
    if (mode === 'create') {
      const count = Number(body.count) || 1
      if (def.supportsBulk && count > 1) {
        const r = await api(`/${state.entity}/bulk`, { method: 'POST', body: JSON.stringify(body) })
        log(`批量新增 ${def.label} × ${r.count} 成功`, 'ok')
      } else {
        delete body.count
        const r = await api(`/${state.entity}`, { method: 'POST', body: JSON.stringify(body) })
        log(`新增 ${def.label} #${r.id} 成功`, 'ok')
      }
    } else {
      const r = await api(`/${state.entity}/${row.id}`, { method: 'PATCH', body: JSON.stringify(body) })
      log(`更新 ${def.label} #${row.id} 成功`, 'ok')
    }
    closeModal()
    loadList()
    refreshCounts()
  } catch (e) {
    log(`${mode === 'create' ? '新增' : '更新'} ${def.label} 失败:${e.message}`, 'err')
  }
}

// ─── 自动化引擎控制 ────────────────────────────────────────────────────

const AUTO = {
  poller: null,
  firstSync: true,    // 首次 status 同步后置 false;运行中不再覆盖 config 输入,允许用户编辑后 Stop→Start 应用
  readConfig() {
    const num = (id, fallback) => {
      const v = Number($(`#${id}`).value)
      return Number.isFinite(v) ? v : fallback
    }
    const pct = (id, fallback) => num(id, fallback) / 100
    return {
      events_per_min:       num('auto-rate', 60),
      register_weight:      pct('auto-reg', 25),
      advances_per_min:     num('auto-adv-rate', 30),
      pending_to_paid:      pct('tr-pp', 60),
      pending_to_cancel:    pct('tr-pc', 10),
      paid_to_shipped:      pct('tr-ps', 60),
      paid_to_refunded:     0,
      shipped_to_completed: pct('tr-sc', 80),
      backfill_enabled:     $('#bf-enabled').checked,
      backfill_start_date:  $('#bf-start').value || null,
      backfill_end_date:    $('#bf-end').value   || null,
    }
  },
  syncBackfillState() {
    const on = $('#bf-enabled').checked
    $('#bf-start').disabled = !on
    $('#bf-end').disabled   = !on
  },
  async start() {
    const body = AUTO.readConfig()
    try {
      const r = await fetch('/api/automation/start', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      const j = await r.json()
      log(`自动化已启动 @ ${body.events_per_min}/min 生成, ${body.advances_per_min}/min 推进`, 'ok')
      AUTO.applyStatus(j.data)
    } catch (e) {
      log(`自动化启动失败:${e.message}`, 'err')
    }
  },
  async stop() {
    try {
      const r = await fetch('/api/automation/stop', { method: 'POST' })
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      const j = await r.json()
      log('自动化已停止', 'ok')
      AUTO.applyStatus(j.data)
    } catch (e) {
      log(`自动化停止失败:${e.message}`, 'err')
    }
  },
  async refresh() {
    try {
      const r = await fetch('/api/automation/status')
      if (!r.ok) return
      const j = await r.json()
      AUTO.applyStatus(j.data)
    } catch { /* 静默 */ }
  },
  applyStatus(s) {
    const running = !!s?.running
    $('#auto-dot').classList.toggle('on', running)
    $('#auto-state-text').textContent = running ? '运行中' : '未启动'
    $('#auto-start').disabled = running
    $('#auto-stop').disabled = !running
    const t = s?.stats?.started_at
    $('#auto-elapsed').textContent = t
      ? `· 自 ${new Date(t + 'Z').toLocaleTimeString('zh-CN', { hour12: false })} 开始`
      : ''
    const st = s?.stats ?? {}
    const set = (id, v) => { $(`#${id}`).textContent = (v ?? 0).toLocaleString() }
    set('auto-registered',    st.registered)
    set('auto-ordered',       st.ordered)
    set('auto-skip-cust',     st.skipped_no_customer)
    set('auto-skip-prod',     st.skipped_no_product)
    set('auto-adv-paid',      st.adv_paid)
    set('auto-adv-cancelled', st.adv_cancelled)
    set('auto-adv-shipped',   st.adv_shipped)
    set('auto-adv-completed', st.adv_completed)
    // Config 输入:**只在首次加载**同步;之后用户的输入是真理,Stop→Start 后才以 readConfig() 的当前值应用
    if (s?.config && AUTO.firstSync) {
      const c = s.config
      const setNum = (id, v) => { if (typeof v === 'number') $(`#${id}`).value = v }
      const setPct = (id, v) => { if (typeof v === 'number') $(`#${id}`).value = Math.round(v * 100) }
      setNum('auto-rate',     c.events_per_min)
      setPct('auto-reg',      c.register_weight)
      setNum('auto-adv-rate', c.advances_per_min)
      setPct('tr-pp',         c.pending_to_paid)
      setPct('tr-pc',         c.pending_to_cancel)
      setPct('tr-ps',         c.paid_to_shipped)
      setPct('tr-sc',         c.shipped_to_completed)
      if (typeof c.backfill_enabled === 'boolean') $('#bf-enabled').checked = c.backfill_enabled
      if (c.backfill_start_date) $('#bf-start').value = c.backfill_start_date
      if (c.backfill_end_date)   $('#bf-end').value   = c.backfill_end_date
      AUTO.syncBackfillState()
      AUTO.firstSync = false
    }
  },
  bind() {
    $('#auto-start').addEventListener('click', AUTO.start)
    $('#auto-stop').addEventListener('click', AUTO.stop)
    $('#bf-enabled').addEventListener('change', AUTO.syncBackfillState)
    // 默认填:30 天前 → 今天
    const today = new Date()
    const past = new Date(today.getTime() - 29 * 86400 * 1000)
    const iso = (d) => d.toISOString().slice(0, 10)
    if (!$('#bf-start').value) $('#bf-start').value = iso(past)
    if (!$('#bf-end').value)   $('#bf-end').value   = iso(today)
    AUTO.syncBackfillState()
    if (!AUTO.poller) AUTO.poller = setInterval(AUTO.refresh, 2000)
  },
}

// ─── 工具 ───────────────────────────────────────────────────────────

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  })[c])
}

// ─── 绑定 ───────────────────────────────────────────────────────────

$$('.tab').forEach((tab) => {
  tab.addEventListener('click', () => {
    $$('.tab').forEach((t) => t.classList.toggle('active', t === tab))
    const key = tab.dataset.tab
    const isAuto = key === 'automation'
    $('#crud-pane').style.display = isAuto ? 'none' : ''
    $('#auto-pane').style.display = isAuto ? '' : 'none'
    if (isAuto) {
      AUTO.refresh()
      return
    }
    state.entity = key
    state.page = 1
    state.filters = {}
    renderFilterRow()
    loadList()
  })
})

$('#btn-new').addEventListener('click', () => openModal('create', null))
$('#btn-bulk-del').addEventListener('click', bulkDeleteSelected)
$('#btn-clear-log').addEventListener('click', () => { logEl.textContent = '' })
$('#modal-close').addEventListener('click', closeModal)
$('#modal-cancel').addEventListener('click', closeModal)
$('#modal-save').addEventListener('click', submitModal)
$('#modal-mask').addEventListener('click', (e) => { if (e.target === e.currentTarget) closeModal() })

// 初次加载 + 5s 自动刷新计数 + 自动化模块绑定
renderFilterRow()
loadList()
refreshCounts()
setInterval(refreshCounts, 5000)
AUTO.bind()
AUTO.refresh()
