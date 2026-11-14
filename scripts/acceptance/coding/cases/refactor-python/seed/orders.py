"""订单统计：按客户/商品分组求和。"""


def total_by_customer(orders):
    result = {}
    for order in orders:
        key = order["customer"]
        result[key] = result.get(key, 0) + order["amount"]
    return result


def total_by_product(orders):
    result = {}
    for order in orders:
        key = order["product"]
        result[key] = result.get(key, 0) + order["amount"]
    return result
