/**
 * 后端 API 客户端。
 * 所有请求统一走 ApiClient.request，返回值约定 `{ code, message, data }`。
 */

export const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8000/api'

interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

type QueryValue = string | number | boolean | undefined | null
type ApiErrorPayload = {
  message?: string
  detail?: string | { message?: string } | Array<{ msg?: string }>
}

/** 把 `{a:1, b:undefined, c:'x'}` 编码为 `a=1&c=x`。 */
function qs(params: Record<string, QueryValue>): string {
  const searchParams = new URLSearchParams()

  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null) {
      continue
    }

    searchParams.append(key, String(value))
  }

  const queryString = searchParams.toString()
  return queryString ? `?${queryString}` : ''
}

class ApiClient {
  private token: string | null = null

  setToken(token: string) {
    this.token = token
  }

  clearToken() {
    this.token = null
  }

  private async request<T = unknown>(
    method: string,
    endpoint: string,
    body?: unknown,
  ): Promise<T> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`
    }

    const res = await fetch(`${API_BASE}${endpoint}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    })

    if (!res.ok) {
      const err: ApiErrorPayload = await res.json().catch(() => ({}))
      const detail = Array.isArray(err.detail)
        ? err.detail.map((e) => e.msg).filter(Boolean).join('; ')
        : typeof err.detail === 'object'
          ? err.detail?.message
          : err.detail
      throw new Error(err.message || detail || `HTTP ${res.status}`)
    }

    const json: ApiResponse<T> = await res.json()

    if (json.code !== 200) {
      throw new Error(json.message || 'Unknown error')
    }

    return json.data
  }

  // ─── Auth ─────────────────────────────────────────────────────────────
  login(username: string, password: string) {
    return this.request<any>('POST', '/auth/login', { username, password })
  }

  sendAdminCode(email: string) {
    return this.request<any>('POST', '/auth/admin/send-code', { email })
  }

  registerAdmin(body: { username: string; email: string; password: string; code: string }) {
    return this.request<any>('POST', '/auth/admin/register', body)
  }

  logout() {
    return this.request<any>('POST', '/auth/logout')
  }

  getCurrentUser() {
    return this.request<any>('GET', '/auth/me')
  }

  updateProfile(payload: { username?: string; email?: string }) {
    return this.request<any>('PATCH', '/auth/me', payload)
  }

  changePassword(payload: { old_password: string; new_password: string }) {
    return this.request<any>('POST', '/auth/me/password', payload)
  }

  // ─── Sales ────────────────────────────────────────────────────────────
  getSalesOverview(dateRange = '30') {
    return this.request<any>(
      'GET',
      `/sales/overview${qs({ date_range: dateRange })}`,
    )
  }

  getSalesTrend(days = 30) {
    return this.request<any>('GET', `/sales/trend${qs({ days })}`)
  }

  getSalesByCategory(dateRange = '30') {
    return this.request<any>(
      'GET',
      `/sales/by-category${qs({ date_range: dateRange })}`,
    )
  }

  getTopProducts(limit = 10, dateRange = '30') {
    return this.request<any>(
      'GET',
      `/sales/top-products${qs({ limit, date_range: dateRange })}`,
    )
  }

  // ─── Products ─────────────────────────────────────────────────────────
  getProductsOverview() {
    return this.request<any>('GET', '/products/overview')
  }

  getProductsByCategory() {
    return this.request<any>('GET', '/products/by-category')
  }

  getLowStockProducts() {
    return this.request<any>('GET', '/products/low-stock')
  }

  getProductsPerformance(dateRange = '30', limit = 20) {
    return this.request<any>(
      'GET',
      `/products/performance${qs({ date_range: dateRange, limit })}`,
    )
  }

  getTopProductsTrend(days = 30, limit = 5) {
    return this.request<any>('GET', `/products/top-trend${qs({ days, limit })}`)
  }

  getCategoryDailyTop(date: string, category: string, limit = 5) {
    return this.request<any>(
      'GET',
      `/products/category-daily-top${qs({ date, category, limit })}`,
    )
  }

  getProductHighlights(days = 7, limit = 8) {
    return this.request<any>('GET', `/products/highlights${qs({ days, limit })}`)
  }

  getManagedProducts(
    page = 1,
    pageSize = 20,
    filters: { category?: string; status?: string; keyword?: string } = {},
  ) {
    return this.request<any>(
      'GET',
      `/products/manage/list${qs({
        page,
        page_size: pageSize,
        ...filters,
      })}`,
    )
  }

  createManagedProduct(payload: {
    product_name: string
    category: string
    price: number
    cost: number
    stock: number
    low_stock_threshold: number
    status: string
  }) {
    return this.request<any>('POST', '/products/manage', payload)
  }

  updateManagedProduct(
    id: number,
    payload: Partial<{
      product_name: string
      category: string
      price: number
      cost: number
      stock: number
      low_stock_threshold: number
      status: string
    }>,
  ) {
    return this.request<any>('PATCH', `/products/manage/${id}`, payload)
  }

  deleteManagedProduct(id: number) {
    return this.request<any>('DELETE', `/products/manage/${id}`)
  }

  // ─── Users / Customers ────────────────────────────────────────────────
  getUsersOverview() {
    return this.request<any>('GET', '/users/overview')
  }

  getUsersByAgeGroup() {
    return this.request<any>('GET', '/users/by-age-group')
  }

  getUsersByProvince() {
    return this.request<any>('GET', '/users/by-province')
  }

  getUsersByGender() {
    return this.request<any>('GET', '/users/by-gender')
  }

  getUserGrowth(days = 30) {
    return this.request<any>('GET', `/users/growth${qs({ days })}`)
  }

  getCustomersList(
    page = 1,
    pageSize = 20,
    filters: { gender?: string; age_group?: string; province?: string; customer_type?: string } = {},
  ) {
    return this.request<any>(
      'GET',
      `/users/customers/list${qs({
        page,
        page_size: pageSize,
        ...filters,
      })}`,
    )
  }

  // ─── Orders ───────────────────────────────────────────────────────────
  getOrdersOverview(dateRange = '30') {
    return this.request<any>('GET', `/orders/overview${qs({ date_range: dateRange })}`)
  }

  getOrdersByStatus(dateRange = '30') {
    return this.request<any>('GET', `/orders/by-status${qs({ date_range: dateRange })}`)
  }

  getOrderTimeline(days = 30) {
    return this.request<any>('GET', `/orders/timeline${qs({ days })}`)
  }

  getOrdersList(page = 1, pageSize = 20, status?: string, date?: string) {
    return this.request<any>(
      'GET',
      `/orders/list${qs({ page, page_size: pageSize, status, date })}`,
    )
  }

  // ─── Finance ──────────────────────────────────────────────────────────
  getFinanceKPI(dateRange = '30') {
    return this.request<any>('GET', `/finance/kpi${qs({ date_range: dateRange })}`)
  }

  getFinanceTrend(days = 30) {
    return this.request<any>('GET', `/finance/trend${qs({ days })}`)
  }

  getExpenseBreakdown(dateRange = '30') {
    return this.request<any>('GET', `/finance/expense-breakdown${qs({ date_range: dateRange })}`)
  }

  getFinanceRecords(page = 1, pageSize = 20, type?: string, category?: string, date?: string) {
    return this.request<any>(
      'GET',
      `/finance/records${qs({
        page,
        page_size: pageSize,
        type,
        category,
        date,
      })}`,
    )
  }

  // ─── Notifications ────────────────────────────────────────────────────
  getNotifications(page = 1, pageSize = 50, isRead?: boolean) {
    return this.request<any>(
      'GET',
      `/notifications/list${qs({
        page,
        page_size: pageSize,
        is_read: isRead,
      })}`,
    )
  }

  getUnreadCount() {
    return this.request<any>('GET', '/notifications/unread-count')
  }

  getNotification(id: number) {
    return this.request<any>('GET', `/notifications/${id}`)
  }

  markNotificationAsRead(id: number) {
    return this.request<any>('PATCH', `/notifications/${id}/read`)
  }

  markBatchAsRead(ids: number[]) {
    return this.request<any>('PATCH', '/notifications/batch/read', { notification_ids: ids })
  }

  deleteNotification(id: number) {
    return this.request<any>('DELETE', `/notifications/${id}`)
  }

  deleteBatchNotifications(ids: number[]) {
    return this.request<any>('DELETE', '/notifications/batch', { notification_ids: ids })
  }

  // ─── System (admin) ───────────────────────────────────────────────────
  getEmployees(page = 1, pageSize = 10) {
    return this.request<any>('GET', `/system/employees${qs({ page, page_size: pageSize })}`)
  }

  getEmployee(id: number) {
    return this.request<any>('GET', `/system/employees/${id}`)
  }

  createEmployee(payload: { username: string; email: string; password: string }) {
    return this.request<any>('POST', '/system/employees', payload)
  }

  updateEmployee(id: number, payload: { is_active?: boolean }) {
    return this.request<any>('PATCH', `/system/employees/${id}`, payload)
  }

  updateEmployeePermissions(id: number, moduleKey: string, action: 'grant' | 'revoke') {
    return this.request<any>('PATCH', `/system/employees/${id}/permissions`, {
      module_key: moduleKey,
      action,
    })
  }

  getModules() {
    return this.request<any>('GET', '/system/modules')
  }

  getPermissionLogs(page = 1, pageSize = 20) {
    return this.request<any>('GET', `/system/permission-logs${qs({ page, page_size: pageSize })}`)
  }
}

export const api = new ApiClient()
