ALTER TABLE finance_records
MODIFY COLUMN category ENUM(
  'sales_income',
  'product_cost',
  'logistics_cost',
  'ad_cost',
  'refund_out'
) NOT NULL;
