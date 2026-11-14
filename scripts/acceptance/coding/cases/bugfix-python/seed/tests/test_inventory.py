from inventory import low_stock, total_value

ITEMS = [
    {"sku": "A", "price": 10.0, "quantity": 2},
    {"sku": "B", "price": 5.5, "quantity": 4},
]


def test_total_value_uses_quantity():
    assert total_value(ITEMS) == 42.0


def test_total_value_empty():
    assert total_value([]) == 0


def test_low_stock():
    assert low_stock(ITEMS) == ["A", "B"]


def test_low_stock_threshold():
    assert low_stock(ITEMS, 3) == ["A"]
