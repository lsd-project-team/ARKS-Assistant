"""购物车。"""


class Cart:
    def __init__(self):
        self._items = []

    def add(self, item):
        self._items.append(item)
        return self

    def remove(self, index):
        del self._items[index]
        return self

    @property
    def items(self):
        return list(self._items)

    def __len__(self):
        return len(self._items)
