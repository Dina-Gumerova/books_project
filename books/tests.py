import json
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, SimpleTestCase, override_settings
from django.urls import reverse


class CatalogTests(SimpleTestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name) / "books"
        self.settings_override = override_settings(BOOKS_DIR=self.folder)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.book = {
            "title": "Тестовая книга", "author": "Иван Иванов",
            "year": 2020, "genre": "Роман", "pages": 200,
            "description": "Описание книги",
        }

    def upload(self, content, name="books.json"):
        if not isinstance(content, bytes):
            content = json.dumps(content, ensure_ascii=False).encode("utf-8")
        file = SimpleUploadedFile(name, content, content_type="application/json")
        return self.client.post(reverse("books:index"), {"action": "upload", "file": file})

    def saved_files(self):
        return list(self.folder.iterdir()) if self.folder.exists() else []

    def test_empty_folder(self):
        response = self.client.get(reverse("books:index"))
        self.assertContains(response, "На сервере пока нет JSON-файлов")
        self.assertEqual(response.context["total_books"], 0)

    def test_add_and_read_book(self):
        response = self.client.post("/", {"action": "add", **self.book}, follow=True)
        self.assertContains(response, "Книга добавлена и сохранена в JSON.")
        path = self.saved_files()[0]
        self.assertRegex(path.name, r"^[0-9a-f]{32}\.json$")
        self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"books": [self.book]})
        self.assertEqual(response.context["books"], [self.book])

    def test_invalid_form_is_not_saved(self):
        for fields in ({"title": " "}, {"author": ""}, {"year": date.today().year + 1},
                       {"pages": 0}, {"genre": "Несуществующий жанр"}, {"title": "x" * 201}):
            with self.subTest(fields=fields):
                response = self.client.post("/", {"action": "add", **self.book, **fields})
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["book_form"].errors)
                self.assertEqual(self.saved_files(), [])

    def test_upload_uses_new_names(self):
        for _ in range(2):
            response = self.upload({"books": [self.book]}, "../../same.json")
            self.assertEqual(response.status_code, 302)
        paths = self.saved_files()
        self.assertEqual(len(paths), 2)
        for path in paths:
            self.assertRegex(path.name, r"^[0-9a-f]{32}\.json$")
        self.assertFalse((Path(self.temporary.name) / "same.json").exists())

    def test_bom_and_uppercase_extension(self):
        content = json.dumps({"books": [self.book]}, ensure_ascii=False).encode("utf-8-sig")
        self.assertEqual(self.upload(content, "BOOKS.JSON").status_code, 302)

    def test_invalid_upload_is_deleted(self):
        invalid = [
            b"not json", b"\xff\xfe", [], {}, {"books": []}, {"books": "text"},
            {"books": [None]}, {"books": [{"title": "Only title"}]},
            {"books": [{**self.book, "pages": "200"}]},
            {"books": [{**self.book, "pages": True}]},
            {"books": [{**self.book, "year": 2020.5}]},
            {"books": [{**self.book, "title": 123}]},
            {"books": [{**self.book, "genre": "Unknown"}]},
            {"books": [{**self.book, "extra": "Unknown"}]},
            {"books": [{**self.book, "year": date.today().year + 1}]},
            {"books": [self.book, {**self.book, "pages": -1}]},
        ]
        for content in invalid:
            with self.subTest(content=content):
                response = self.upload(content)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["upload_form"].errors)
                self.assertEqual(self.saved_files(), [])

    def test_wrong_extension_and_large_file(self):
        response = self.upload({"books": [self.book]}, "books.txt")
        self.assertContains(response, "Нужен файл с расширением .json.")
        response = self.upload(b" " * (1024 * 1024 + 1))
        self.assertContains(response, "Размер файла не должен превышать 1 МБ.")
        self.assertEqual(self.saved_files(), [])

    def test_all_files_filter_and_statistics(self):
        self.upload({"books": [self.book]})
        second = {**self.book, "title": "Другая книга", "genre": "Повесть", "pages": 100}
        self.upload({"books": [second]})
        response = self.client.get("/", {"genre": "Повесть"})
        self.assertEqual(response.context["books"], [second])
        self.assertEqual(response.context["total_books"], 2)
        self.assertEqual(response.context["total_authors"], 1)
        self.assertEqual(response.context["average_pages"], 150)
        self.assertEqual(len(response.context["files"]), 2)

    def test_damaged_file_does_not_break_catalog(self):
        self.upload({"books": [self.book]})
        (self.folder / "broken.json").write_text("{broken", encoding="utf-8")
        response = self.client.get("/")
        self.assertContains(response, "Файл broken.json:")
        self.assertEqual(response.context["total_books"], 1)

    def test_download_and_import_again(self):
        self.upload({"books": [self.book]})
        name = self.saved_files()[0].name
        for url in (reverse("books:download_file", args=[name]), reverse("books:download_all")):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertIn("attachment", response["Content-Disposition"])
            self.assertEqual(response.json(), {"books": [self.book]})
        self.assertEqual(self.upload(response.content).status_code, 302)

    def test_missing_and_unsafe_downloads(self):
        for filename in ("missing.json", "../outside.json", "..\\outside.json", "settings.py"):
            response = self.client.get("/download/" + filename + "/")
            self.assertEqual(response.status_code, 404)

    def test_empty_export(self):
        response = self.client.get(reverse("books:download_all"), follow=True)
        self.assertContains(response, "Пока нет книг для скачивания.")

    def test_html_in_data_is_escaped(self):
        book = {**self.book, "title": "<script>alert(1)</script>"}
        self.upload({"books": [book]})
        response = self.client.get("/")
        self.assertNotContains(response, "<script>alert(1)</script>")
        self.assertContains(response, "&lt;script&gt;alert(1)&lt;/script&gt;")

    def test_csrf_is_required(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post("/", {"action": "add", **self.book})
        self.assertEqual(response.status_code, 403)
        client.get("/")
        response = client.post("/", {
            "action": "add", **self.book,
            "csrfmiddlewaretoken": client.cookies["csrftoken"].value,
        })
        self.assertEqual(response.status_code, 302)
