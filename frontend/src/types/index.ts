// 角色
export type Role = 'admin' | 'staff'

// 导航菜单项
export interface NavItem {
  id: string
  label: string
  icon: string
  path: string
  adminOnly: boolean
  /** 对应后端 module_key;非 admin 角色按 permissions 判断显示。adminOnly 项可不填。 */
  moduleKey?: string
}

// 表格列定义
export interface TableColumn<T = Record<string, unknown>> {
  key: string
  title: string
  align?: 'left' | 'right' | 'center'
  wrap?: boolean
  render?: (value: unknown, row: T, index: number) => unknown
  /** 自定义表头渲染(覆盖 title 文本显示);用于在表头放过滤器、复选框等 */
  headerRender?: () => unknown
}

// Badge 颜色
export type BadgeColor = 'green' | 'red' | 'yellow' | 'blue' | 'purple' | 'gray' | 'orange'

// 通知
export type NotificationType = '库存预警' | '大额退款' | '异常订单' | '销售额波动'

export interface Notification {
  id: number
  type: NotificationType
  title: string
  content: string
  read: boolean
  time: string
}

// 商品
export interface ProductPerformance {
  product_id: number
  product_name: string
  category: string
  price: number
  quantity_sold: number
  sales: number
  profit: number
  profit_margin: number
}

export interface LowStockProduct {
  id: number
  product_name: string
  category: string
  stock: number
  low_stock_threshold: number
  price: number
  status: string
}

// 订单
export interface OrderListItem {
  order_id: number
  order_no: string
  customer: string
  total_amount: number
  status: string
  created_at: string | null
}

// 财务
export interface FinanceRecord {
  id: number
  type: string
  category: string
  amount: number
  order_no: string | null
  recorded_at: string | null
}

// 员工(后端形状)
export interface Employee {
  id: number
  username: string
  email: string
  is_active: boolean
  created_at: string | null
  last_login_at: string | null
  permissions: string[]
}

// 模块
export interface SystemModule {
  id: number
  module_key: string
  module_name: string
  description: string | null
  sort_order: number
}

// 权限变更日志
export interface PermissionLog {
  id: number
  admin_username: string
  target_username: string
  module_key: string
  action: 'grant' | 'revoke'
  changed_at: string | null
  remark: string | null
}

