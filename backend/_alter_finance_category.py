"""一次性脚本:扩展 finance_records.category ENUM,添加 'product_cost'。

新规则下,订单从 pending → paid 时会写入 product_cost FinanceRecord,
所以 DB enum 必须先支持该值,否则插入会失败。

用法:python _alter_finance_category.py
"""
from sqlalchemy import text
from database import engine


NEW_ENUM = (
    "ENUM('sales_income','product_cost','logistics_cost','ad_cost','refund_out')"
)


def main():
    with engine.begin() as conn:
        sql = f"ALTER TABLE finance_records MODIFY COLUMN category {NEW_ENUM} NOT NULL"
        print(f"[alter] {sql}")
        conn.execute(text(sql))
        print("[alter] done.")


if __name__ == "__main__":
    main()
