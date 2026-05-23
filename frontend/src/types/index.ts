/* 前端通用类型定义 */

export type Role = 'admin' | 'staff'

export interface NavItem {
  id: string
  label: string
  icon: string
  path: string
  adminOnly: boolean
  
  moduleKey?: string
}

export interface TableColumn<T = Record<string, unknown>> {
  key: string
  title: string
  align?: 'left' | 'right' | 'center'
  wrap?: boolean
  render?: (value: unknown, row: T, index: number) => unknown
  
  headerRender?: () => unknown
}

export type BadgeColor =
  | 'green'
  | 'red'
  | 'yellow'
  | 'blue'
  | 'purple'
  | 'gray'
  | 'orange'

export type NotificationType =
  | '库存预警'
  | '大额退款'
  | '异常订单'
  | '销售额波动'

export interface Notification {
  id: number
  type: NotificationType
  title: string
  content: string
  read: boolean
  time: string
}

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

export interface OrderListItem {
  order_id: number
  order_no: string
  customer: string
  total_amount: number
  status: string
  created_at: string | null
}

export interface FinanceRecord {
  id: number
  type: string
  category: string
  amount: number
  order_no: string | null
  recorded_at: string | null
}

export interface Employee {
  id: number
  username: string
  email: string
  is_active: boolean
  created_at: string | null
  last_login_at: string | null
  permissions: string[]
}

export interface SystemModule {
  id: number
  module_key: string
  module_name: string
  description: string | null
  sort_order: number
}

export interface PermissionLog {
  id: number
  admin_username: string
  target_username: string
  module_key: string
  action: 'grant' | 'revoke'
  changed_at: string | null
  remark: string | null
}
