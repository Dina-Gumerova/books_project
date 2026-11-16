from pathlib import Path

from django.contrib import messages
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from .forms import BookForm, UploadForm, GENRES
from .storage import data_folder, import_file, load_catalog, read_books, save_book


@require_http_methods(["GET", "POST"])
def index(request):
    book_form = BookForm()
    upload_form = UploadForm()

    if request.method == "POST":
        if request.POST.get("action") == "add":
            book_form = BookForm(request.POST)
            if book_form.is_valid():
                try:
                    save_book(book_form.cleaned_data)
                except OSError:
                    book_form.add_error(None, "Не удалось сохранить файл. Проверьте доступ к папке data/books.")
                else:
                    messages.success(request, "Книга добавлена и сохранена в JSON.")
                    return redirect("books:index")
        elif request.POST.get("action") == "upload":
            upload_form = UploadForm(request.POST, request.FILES)
            if upload_form.is_valid():
                try:
                    count = import_file(upload_form.cleaned_data["file"])
                except ValueError as error:
                    upload_form.add_error("file", str(error))
                except OSError:
                    upload_form.add_error("file", "Не удалось сохранить файл. Проверьте доступ к папке data/books.")
                else:
                    messages.success(request, f"Файл загружен. Книг добавлено: {count}.")
                    return redirect("books:index")

    try:
        all_books, files, errors = load_catalog()
    except OSError:
        all_books, files = [], []
        errors = ["Не удалось прочитать папку data/books. Проверьте права доступа."]
    genre = request.GET.get("genre", "")
    books = [book for book in all_books if book["genre"] == genre] if genre else all_books
    count = len(all_books)
    context = {
        "book_form": book_form, "upload_form": upload_form,
        "books": books, "files": files, "file_errors": errors,
        "genres": GENRES, "current_genre": genre,
        "total_books": count,
        "total_authors": len({book["author"].casefold() for book in all_books}),
        "average_pages": round(sum(book["pages"] for book in all_books) / count) if count else 0,
    }
    return render(request, "books/index.html", context)


def json_download(books, filename):
    response = JsonResponse({"books": books}, json_dumps_params={"ensure_ascii": False, "indent": 4})
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@require_GET
def download_file(request, filename):
    # Можно скачать только обычный JSON-файл из папки книг.
    if Path(filename).name != filename or "\\" in filename or Path(filename).suffix.lower() != ".json":
        raise Http404("Файл не найден")
    path = data_folder() / filename
    if not path.is_file() or path.is_symlink():
        raise Http404("Файл не найден")
    try:
        books = read_books(path)
    except (ValueError, OSError):
        raise Http404("Файл отсутствует или содержит неверные данные")
    return json_download(books, "books.json")


@require_GET
def download_all(request):
    books, files, errors = load_catalog()
    if not books:
        messages.info(request, "Пока нет книг для скачивания.")
        return redirect("books:index")
    return json_download(books, "all_books.json")
