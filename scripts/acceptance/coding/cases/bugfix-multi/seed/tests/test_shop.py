import pytest

from shop import Cart, apply_discount, line_total, order_total

ITEMS = [
    {"price": 10, "quantity": 2},
    {"price": 5, "quantity": 4},
]


def test_line_total():
    assert line_total(ITEMS[0]) == 20


def test_order_total_without_discount():
    assert order_total(ITEMS) == 40


def test_order_total_with_discount():
    assert order_total(ITEMS, 25) == 30


def test_order_total_full_discount():
    assert order_total(ITEMS, 100) == 0


def test_discount_range_is_validated():
    with pytest.raises(ValueError):
        order_total(ITEMS, -1)
    with pytest.raises(ValueError):
        order_total(ITEMS, 101)


def test_cart_add_remove():
    cart = Cart().add(ITEMS[0]).add(ITEMS[1])
    assert len(cart) == 2
    cart.remove(0)
    assert len(cart) == 1 and cart.items[0] == ITEMS[1]
