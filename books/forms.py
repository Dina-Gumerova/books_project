from datetime import date
from pathlib import Path

from django import forms
from django.conf import settings

GENRES = ["Роман", "Повесть", "Рассказ", "Фантастика", "Учебная литература", "Другое"]


class BookForm(forms.Form):
    title = forms.CharField(label="Название", max_length=200)
    author = forms.CharField(label="Автор", max_length=100)
    year = forms.IntegerField(label="Год издания", min_value=1, max_value=date.today().year)
    genre = forms.ChoiceField(label="Жанр", choices=[(item, item) for item in GENRES])
    pages = forms.IntegerField(label="Количество страниц", min_value=1, max_value=10000)
    description = forms.CharField(
        label="Описание", required=False, max_length=1000,
        widget=forms.Textarea(attrs={"rows": 3}),
    )


class UploadForm(forms.Form):
    file = forms.FileField(
        label="Файл с книгами", widget=forms.FileInput(attrs={"accept": ".json"}),
    )

    def clean_file(self):
        file = self.cleaned_data["file"]
        if Path(file.name).suffix.lower() != ".json":
            raise forms.ValidationError("Нужен файл с расширением .json.")
        if file.size > settings.MAX_JSON_SIZE:
            raise forms.ValidationError("Размер файла не должен превышать 1 МБ.")
        return file
