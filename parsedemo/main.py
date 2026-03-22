"""
Консольный batch-вызов POST /parse_demo (как desktop, без PyQt).

Запуск из корня репозитория:
  python parsedemo/main.py
  python parsedemo/main.py --file parsedemo/urls.json --base-url http://localhost:8000

Требуется запущенный backend (run.py / uvicorn).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, List

DEFAULT_BASE_URL = "http://localhost:8000"
BAR_WIDTH = 20


def print_json_help() -> None:
    print()
    print("  Входной JSON (файл в папке parsedemo, по умолчанию urls.json)")
    print("  — допустимы два формата:")
    print()
    print('    1) Массив строк в корне:')
    print('       [ "https://site1.com", "https://site2.com/page" ]')
    print()
    print('    2) Объект с полем "urls":')
    print('       { "urls": [ "https://a.com", "https://b.com" ] }')
    print()
    print("  Протокол https/http можно указывать явно; без схемы backend сам допишет https://")
    print()


def load_urls(path: Path) -> List[str]:
    text = path.read_text(encoding="utf-8")
    raw: Any = json.loads(text)
    out: List[str] = []
    if isinstance(raw, list):
        out = [str(u).strip() for u in raw if str(u).strip()]
    elif isinstance(raw, dict) and "urls" in raw and isinstance(raw["urls"], list):
        out = [str(u).strip() for u in raw["urls"] if str(u).strip()]
    else:
        raise ValueError(
            "Ожидался JSON: массив URL или объект {\"urls\": [ ... ]}"
        )
    return out


def progress_bar(completed: int, total: int, width: int = BAR_WIDTH) -> str:
    if total <= 0:
        return "[" + " " * width + "] 0%"
    pct = int(100 * completed / total)
    filled = int(round(width * completed / total))
    filled = max(0, min(filled, width))
    bar = "=" * filled + " " * (width - filled)
    return f"[{bar}] {pct}%"


def post_parse_demo(base_url: str, url: str, timeout: int = 120) -> dict[str, Any]:
    base = base_url.rstrip("/")
    payload = json.dumps({"url": url}).encode("utf-8")
    req = urllib.request.Request(
        f"{base}/parse_demo",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8")
            data = json.loads(err_body) if err_body else {}
        except json.JSONDecodeError:
            data = {"success": False, "error": e.reason or str(e)}
        if isinstance(data, dict) and "success" not in data:
            data["success"] = False
        return data if isinstance(data, dict) else {"success": False, "error": str(data)}
    except urllib.error.URLError as e:
        return {"success": False, "error": str(e.reason or e)}
    except TimeoutError:
        return {"success": False, "error": "Таймаут запроса"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def main() -> None:
    script_dir = Path(__file__).resolve().parent
    default_file = script_dir / "urls.json"

    parser = argparse.ArgumentParser(
        description="Пакетный вызов API parse_demo для списка URL из JSON-файла."
    )
    parser.add_argument(
        "--file",
        "-f",
        type=Path,
        default=default_file,
        help=f"Путь к JSON с URL (по умолчанию: {default_file})",
    )
    parser.add_argument(
        "--base-url",
        "-b",
        default=DEFAULT_BASE_URL,
        help=f"Базовый URL backend (по умолчанию: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Таймаут HTTP на один запрос, сек (по умолчанию: 120)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  Parse demo — batch (POST /parse_demo)")
    print("=" * 60)
    print_json_help()

    path: Path = args.file
    if not path.is_file():
        print(f"Файл не найден: {path}")
        print(f"Создайте его или скопируйте из {script_dir / 'urls.example.json'}")
        sys.exit(1)

    try:
        urls = load_urls(path)
    except json.JSONDecodeError as e:
        print(f"Ошибка JSON в файле: {e}")
        sys.exit(1)
    except ValueError as e:
        print(e)
        sys.exit(1)

    print(f"  Файл:     {path.resolve()}")
    print(f"  Backend:  {args.base_url}")
    print(f"  URL в списке: {len(urls)}")
    print("-" * 60)

    if not urls:
        print("Список URL пуст — нечего обрабатывать.")
        sys.exit(0)

    t0 = time.perf_counter()
    ok_count = 0
    fail_count = 0

    zero_line = progress_bar(0, len(urls))
    sys.stdout.write(f"\r  {zero_line}  0/{len(urls)}  ")
    sys.stdout.flush()

    for i, url in enumerate(urls, start=1):
        result = post_parse_demo(args.base_url, url, timeout=args.timeout)
        success = bool(result.get("success"))
        if success:
            ok_count += 1
        else:
            fail_count += 1

        line = progress_bar(i, len(urls))
        sys.stdout.write(f"\r  {line}  {i}/{len(urls)}  ")
        sys.stdout.flush()

    elapsed = time.perf_counter() - t0
    print()
    print("-" * 60)
    print(f"  Готово.")
    print(f"  Обработано URL: {len(urls)}  (успешно: {ok_count}, с ошибкой: {fail_count})")
    print(f"  Общее время:    {elapsed:.2f} с")
    print("=" * 60)


if __name__ == "__main__":
    main()
