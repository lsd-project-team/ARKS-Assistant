"""价格计算。"""


def line_total(item):
    return item["price"] * item["quantity"]


def apply_discount(amount, percent):
    return amount * (1 - percent / 100)


def order_total(items, discount_percent=0):
    amount = 0
    for item in items:
        amount += line_total(item)
    return amount
