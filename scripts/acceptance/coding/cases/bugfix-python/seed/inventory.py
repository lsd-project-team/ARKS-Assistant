"""库存汇总：计算总价与低库存列表。"""


def total_value(items):
    total = 0
    for item in items:
        total += item["price"]
    return total


def low_stock(items, threshold=5):
    return [item["sku"] for item in items if item["quantity"] < threshold]
