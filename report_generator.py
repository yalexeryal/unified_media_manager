import os
import urllib.parse
from pathlib import Path
from typing import Dict, List
from core.file_utils import format_size


def generate_html_report(duplicates: Dict[str, List[str]], output_path: str = "duplicates_report.html") -> None:
    """
    Генерирует HTML-отчет с карточками дубликатов.
    Пользователь может визуально проверить файлы и увидеть, какой из них предлагается оставить.
    """
    if not duplicates:
        print("📊 Дубликаты не найдены, отчет не создан.")
        return

    html = [
        "<!DOCTYPE html><html lang='ru'><head><meta charset='UTF-8'>",
        "<title>Отчет по дубликатам файлов</title>",
        "<style>",
        "body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 1200px; margin: 20px auto; padding: 0 20px; background: #f5f5f5; }",
        "h1 { color: #333; }",
        ".group { border: 1px solid #ddd; padding: 15px; margin-bottom: 20px; border-radius: 8px; background: #fff; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }",
        ".group h3 { margin-top: 0; color: #555; font-size: 14px; word-break: break-all; }",
        ".file-item { display: flex; align-items: flex-start; padding: 10px; margin: 8px 0; background: #fafafa; border-radius: 6px; border-left: 4px solid #ccc; }",
        ".file-item.keep { background-color: #e8f5e9; border-left-color: #4caf50; }",
        ".file-item.delete { background-color: #ffebee; border-left-color: #f44336; }",
        ".file-item img { max-width: 120px; max-height: 120px; margin-right: 15px; object-fit: cover; border-radius: 4px; background: #eee; }",
        ".file-info { flex-grow: 1; }",
        ".file-path { font-family: 'Consolas', 'Monaco', monospace; font-size: 12px; word-break: break-all; color: #333; }",
        ".file-size { font-size: 12px; color: #666; margin-top: 4px; }",
        ".badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: bold; margin-left: 10px; }",
        ".badge-keep { background: #4caf50; color: white; }",
        ".badge-delete { background: #f44336; color: white; }",
        "</style></head><body>",
        "<h1>📊 Отчет по дубликатам файлов</h1>",
        f"<p>Найдено групп дубликатов: <b>{len(duplicates)}</b></p>",
        "<p><i>💡 Инструкция: В каждой группе первый файл (зеленый) предлагается оставить как оригинал. Остальные (красные) являются дубликатами.</i></p>",
        "<p><i>Откройте этот отчет в браузере. Если превью не отображается, проверьте пути к файлам.</i></p>"
    ]

    for hash_val, paths in duplicates.items():
        html.append(f'<div class="group"><h3>Группа (hash: {hash_val[:16]}...)</h3>')
        for i, path in enumerate(paths):
            css_class = "keep" if i == 0 else "delete"
            badge = '<span class="badge badge-keep">ОРИГИНАЛ (оставить)</span>' if i == 0 else '<span class="badge badge-delete">ДУБЛИКАТ</span>'

            ext = Path(path).suffix.lower()
            preview = ""
            if ext in {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}:
                # Кодируем путь для file:// URI
                file_url = urllib.parse.quote(os.path.abspath(path))
                preview = f'<img src="file:///{file_url}" alt="preview" onerror="this.style.display=\'none\'">'

            try:
                size_str = format_size(os.path.getsize(path))
            except OSError:
                size_str = "Неизвестно"

            html.append(
                f'<div class="file-item {css_class}">'
                f'{preview}'
                f'<div class="file-info">'
                f'<div class="file-path">{path} {badge}</div>'
                f'<div class="file-size">Размер: {size_str}</div>'
                f'</div>'
                f'</div>'
            )
        html.append('</div>')

    html.append("</body></html>")

    abs_output_path = os.path.abspath(output_path)
    with open(abs_output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(html))

    print(f"✅ Отчет создан: {abs_output_path}")
    print("👉 Откройте этот файл в любом браузере для визуальной проверки.")