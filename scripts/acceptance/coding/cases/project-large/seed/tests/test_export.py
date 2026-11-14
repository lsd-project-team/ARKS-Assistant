import csv
import io

from library import LibraryService, books_to_csv


def service():
    svc = LibraryService()
    svc.add_book("B", "Author B", 2021)
    svc.add_book("A", "Author A", 2020)
    return svc


def test_header():
    text = books_to_csv(service())
    assert text.splitlines()[0] == "id,title,author,year"


def test_rows_sorted_by_id():
    rows = list(csv.reader(io.StringIO(books_to_csv(service()))))
    assert [row[1] for row in rows[1:]] == ["B", "A"]


def test_empty():
    assert len(list(csv.reader(io.StringIO(books_to_csv(LibraryService()))))) == 1
