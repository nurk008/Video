---
trigger: glob
globs: "production/*.py, production/*.sh, output/server.py, output/index.html"
description: "Technical invariants and verification checklist for episode video/audio rendering scripts in production/ and preview tools in output/."
---

# Технические стандарты видео-конвейера (`production/`)

При создании или правке сборочных скриптов ориентируйся на актуальные эталоны @production/build_ep05_kz.py и @production/anim_ep05.py (3D-рельефные тактические карты `MapCamera` и кинетическая графика), а также @production/build_ep04_neural.py, @production/render.py и @production/sfx.py.

## 1. Обязательные параметры рендера
* **Формат видео:** вертикальный `1080×1920` (`9:16`), ровно `30 fps`, кодек `libx264`, `yuv420p`.
* **Озвучка (`edge-tts`):** с `EP04+` по умолчанию собираем **только `kz`** (`kk-KZ-DauletNeural`, fallback `kk-KZ-AigulNeural`, `rate="-2%"`, `pitch="-2Hz"`), если пользователь явно не попросил добавить `ru`/`en`.
* **Звук:** `48000 Hz`, нормализация итогового микса строго под **`-14 LUFS`** (`loudnorm`) без клиппинга и **без музыкальных инструментов** (только физические SFX + *A cappella* вокал).
* **Камера без «желе»:** используй **только жёсткое субпиксельное движение камеры** (`rigid_cam` / `rigid_cam_frame`, многоплоскостные сцены и `MapCamera` из `anim_ep05.py`: плавный зум, панорама, микро-толчок удара, атмосферные частицы). Никогда не возвращайся к синусоидальному искажению (`warp_rgb` / `local_animate.py`).

## 2. Портативность путей (Mac + Remote Agents)
* В старых скриптах (`build_ep04_neural.py`, `build_ep05_kz.py`, `anim_ep05.py`) встречается жёсткий путь `/Users/market/antigravity/Video`.
* Во всех **новых** или рефакторируемых скриптах и вспомогательных модулях (включая пути к шрифтам `production/fonts/...`) вычисляй корень проекта динамически через `ROOT = Path(__file__).resolve().parent.parent`, чтобы сборка работала и локально на macOS, и в облачных Remote Agents.

## 3. Обязательная петля проверки (Verification Loop)
После генерации/изменения ролика или сцен **не завершай работу**, пока не проверишь:
1. Фактическое наличие и размер `.mp4` в `output/`.
2. Потоки через `ffprobe`: `1080x1920`, `30 fps`, наличие аудиодорожки, ожидаемая длительность (~100–140 с).
3. Громкость итогового файла (~`-14 LUFS` через `ffmpeg -af loudnorm=print_format=summary`).
4. При правке `output/index.html` или `output/server.py` — проверить отдачу видео с `Range` (HTTP 206) и отсутствие ошибок в браузере.
