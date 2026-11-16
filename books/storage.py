import json
from pathlib import Path
from uuid import uuid4

from django.conf import settings

from .forms import BookForm


def data_folder():
    folder = Path(settings.BOOKS_DIR)
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def validate_data(data):
    if not isinstance(data, dict) or set(data) != {"books"}:
        raise ValueError('В JSON должен быть объект с единственным полем "books".')
    items = data["books"]
    if not isinstance(items, list) or not 1 <= len(items) <= settings.MAX_BOOKS_PER_FILE:
        raise ValueError("Поле books должно содержать список от 1 до 1000 книг.")

    result = []
    required = {"title", "author", "year", "genre", "pages"}
    for number, book in enumerate(items, start=1):
        if not isinstance(book, dict) or not required.issubset(book):
            raise ValueError(f"Книга №{number}: заполните title, author, year, genre, pages.")
        if set(book) - (required | {"description"}):
            raise ValueError(f"Книга №{number}: обнаружены неизвестные поля.")
        for field in ("title", "author", "genre", "description"):
            if field in book and not isinstance(book[field], str):
                raise ValueError(f"Книга №{number}: поле {field} должно быть строкой.")
        for field in ("year", "pages"):
            if type(book[field]) is not int:
                raise ValueError(f"Книга №{number}: поле {field} должно быть целым числом.")

        form = BookForm(book)
        if not form.is_valid():
            details = []
            for field, errors in form.errors.items():
                details.append(f"{form.fields[field].label}: {' '.join(errors)}")
            raise ValueError(f"Книга №{number}. " + " ".join(details))
        result.append(form.cleaned_data)
    return result


def read_books(path):
    if path.stat().st_size > settings.MAX_JSON_SIZE:
        raise ValueError("Размер файла превышает 1 МБ.")
    try:
        with path.open(encoding="utf-8-sig") as file:
            data = json.load(file)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise ValueError("Не удалось прочитать JSON. Проверьте синтаксис и кодировку UTF-8.") from error
    return validate_data(data)


def save_book(book):
    path = data_folder() / (uuid4().hex + ".json")
    temporary = path.with_suffix(".tmp")
    try:
        temporary.write_text(
            json.dumps({"books": [book]}, ensure_ascii=False, indent=4), encoding="utf-8",
        )
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return path.name


def import_file(upload):
    # Имя, переданное пользователем, не используется при сохранении.
    path = data_folder() / (uuid4().hex + ".json")
    temporary = path.with_suffix(".tmp")
    try:
        size = 0
        with temporary.open("wb") as file:
            for chunk in upload.chunks():
                size += len(chunk)
                if size > settings.MAX_JSON_SIZE:
                    raise ValueError("Размер файла превышает 1 МБ.")
                file.write(chunk)
        books = read_books(temporary)
        temporary.replace(path)
    finally:
        # В том числе удаляем неверный файл после неудачной проверки.
        temporary.unlink(missing_ok=True)
    return len(books)


def load_catalog():
    books, files, errors = [], [], []
    for path in sorted(data_folder().iterdir()):
        if path.suffix.lower() != ".json" or not path.is_file() or path.is_symlink():
            continue
        try:
            items = read_books(path)
        except (ValueError, OSError) as error:
            errors.append(f"Файл {path.name}: {error}")
            continue
        files.append({"name": path.name, "count": len(items)})
        books.extend(items)
    return books, files, errors
