from django import forms
from django.core.validators import FileExtensionValidator
from .models import Book, BookNote


class MultipleFileInput(forms.ClearableFileInput):
    """自定义多文件上传widget"""
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """自定义多文件字段"""
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class BookUploadForm(forms.ModelForm):
    """书籍上传表单"""
    
    class Meta:
        model = Book
        fields = ['title', 'file', 'category']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入书籍标题'
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.epub,.mobi,.txt,.docx,.doc'
            }),
            'category': forms.Select(attrs={
                'class': 'form-control'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['file'].validators = [
            FileExtensionValidator(
                allowed_extensions=['pdf', 'epub', 'mobi', 'txt', 'docx', 'doc']
            )
        ]


class BookNoteForm(forms.ModelForm):
    """书籍笔记表单"""
    
    class Meta:
        model = BookNote
        fields = ['note_content', 'note_type', 'color', 'tags']
        widgets = {
            'note_content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': '请输入笔记内容'
            }),
            'note_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'color': forms.Select(attrs={
                'class': 'form-control'
            }),
            'tags': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '标签，用逗号分隔'
            })
        }


class BatchUploadForm(forms.Form):
    """批量上传表单"""
    
    files = MultipleFileField(
        widget=MultipleFileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.epub,.mobi,.txt,.docx,.doc'
        }),
        validators=[
            FileExtensionValidator(
                allowed_extensions=['pdf', 'epub', 'mobi', 'txt', 'docx', 'doc']
            )
        ]
    )
    
    batch_name = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '批量上传名称（可选）'
        })
    ) 