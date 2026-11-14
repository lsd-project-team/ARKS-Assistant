from orders import total_by_customer, total_by_product

ORDERS = [
    {"customer": "A", "product": "X", "amount": 10},
    {"customer": "A", "product": "Y", "amount": 5},
    {"customer": "B", "product": "X", "amount": 7},
]


def test_customer_totals():
    assert total_by_customer(ORDERS) == {"A": 15, "B": 7}


def test_product_totals():
    assert total_by_product(ORDERS) == {"X": 17, "Y": 5}


def test_empty():
    assert total_by_customer([]) == {}
    assert total_by_product([]) == {}


def test_float_amounts():
    orders = [{"customer": "A", "product": "X", "amount": 1.5}]
    assert total_by_customer(orders) == {"A": 1.5}
