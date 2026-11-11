# Статус проекта «Video» (Единая точка продолжения для всех аккаунтов)

Последнее обновление: 2026-11-11

## Что уже полностью готово (лежит в папке проекта и в GitHub):
1. **Стратегия и регламент публикации (`ai_history_channel_guide_and_history.md`)** и **Свод правил контента (`hanafi_ai_content_rules.md`)**.
2. **Выпуск №1: «Курултай в Ордабасы (1726) и Аныракайская битва (1729/1730)» (RU / KZ / EN):**
   * Сценарий: `ordabasy_anyrakai_viral_script.md`, `production/narration_shorts_ep01.json`.
   * Все 23 живые ИИ-видео сцены: `scenes_video/scene_01.mp4` … `scene_20.mp4` (Wan 2.2 14B I2V + LTX-Video-Distilled).
   * Озвучка с замедленным, чётким темпом речи (`length_scale = 1.05–1.08`, паузы `0.28–0.38 сек`) и саунд-дизайн без музыкальных инструментов: `production/voice.py`, `production/sfx.py`, `production/render.py`.
   * Готовые финальные ролики Выпуска №1 (`output/`):
     * `output/EP01_Ordabasy_Shorts_RU.mp4` (`80.4 сек`, `1080×1920`, `30 fps`, `-14 LUFS`)
     * `output/EP01_Ordabasy_Shorts_KZ.mp4` (`90.0 сек`, `1080×1920`, `30 fps`, `-14 LUFS`)
     * `output/EP01_Ordabasy_Shorts_EN.mp4` (`87.7 сек`, `1080×1920`, `30 fps`, `-14 LUFS`)
3. **Выпуск №2: «Орбулакская битва (1643): 600 стрелков Жангир-хана против 50 000» (RU / KZ / EN):**
   * Сценарий и раскадровка (16 динамичных сцен в стиле военного триллера с бесшовной петлёй): `orbulak_1643_viral_script.md`, `production/narration_shorts_ep02.json`.
   * Кадры и все 16 анимированных видеоклипов: `scenes_ep02/` и `scenes_ep02_video/scene_01.mp4` … `scene_16.mp4` (`production/generate_ep02_videos.py`, `production/make_ep02_clips.py`).
   * Полный конвейер озвучки, каньонного саунд-дизайна (рытьё шанцев, шипение фитиля, пауза тишины перед залпом, залпы 600 мушкетов с горным эхом, камнепад, дрожь земли, атака 20 000 всадников Жалантос-бахадура, мужской хор *A cappella*) и рендера: `production/build_ep02.py`.
   * Готовые финальные ролики Выпуска №2 (`output/`):
     * `output/EP02_Orbulak_Shorts_RU.mp4` (`99.7 сек`, `1080×1920`, `30 fps`, `-14 LUFS`)
     * `output/EP02_Orbulak_Shorts_KZ.mp4` (`114.2 сек`, `1080×1920`, `30 fps`, `-14 LUFS`)
     * `output/EP02_Orbulak_Shorts_EN.mp4` (`1080×1920`, `30 fps`, `-14 LUFS`)

---

## Следующий шаг (с чего продолжать на любом аккаунте):
1. При переключении на аккаунт со свежими лимитами `generate_image` / `ZeroGPU` можно при желании догенерировать дополнительные 8k кадры/LTX-клипы через `python production/generate_ep02_videos.py`.
2. Публикация Выпуска №1 и Выпуска №2 (RU / KZ / EN) или переход к Выпуску №3.
