"""CSV 导出。"""

import csv
import io


def books_to_csv(service):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "title", "author", "year"])
    for book in sorted(service.repository.books.values(), key=lambda item: item.id):
        writer.writerow([book.id, book.title, book.author, book.year])
    return buffer.getvalue()
