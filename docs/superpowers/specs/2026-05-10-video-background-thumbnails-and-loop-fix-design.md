# Design: Video Background Thumbnails + Loop Fix

## Overview

Two independent improvements to how video backgrounds behave in OpenLP:

1. **Loop fix** — on Windows, background videos pause or flash black at the end of each loop. Fix by intercepting `EndOfMedia` on background items and seeking back to position 0 instead of relying on Qt's broken native `Loops.Infinite` on Windows.

2. **Video thumbnails** — the Themes panel and the Preview pane both show a black placeholder for video background themes. Fix by extracting a static frame from the video at 1 second in, caching it to disk, and using it as a static image background wherever the live video player is not active.

Both fixes are independent and can be implemented separately.

---

## Fix 1 — Video Loop (Black Screen / Pause on Windows)

### Problem

`MediaPlayer.toggle_loop(True)` sets `QMediaPlayer.setLoops(Infinite)`. On Linux this loops seamlessly. On Windows, the WMF backend emits `EndOfMedia` before restarting the loop, which triggers the stop signal chain and causes a visible pause or black flash.

### Solution

In `openlp/core/ui/media/mediaplayer.py`, in `media_status_changed_event()`, when `EndOfMedia` fires and the item is a background (`controller.media_play_item.is_background == True`), seek to position 0 and continue playing instead of emitting the stop signal.

```python
def media_status_changed_event(self, event):
    if self.controller.media_play_item.media_type == MediaType.Dual:
        return
    if event == QMediaPlayer.MediaStatus.EndOfMedia:
        if self.controller.media_play_item.is_background:
            self.media_player.setPosition(0)
            self.media_player.play()
            return
        if self.controller.is_live:
            Registry().get("media_controller").live_media_status_changed.emit()
        else:
            Registry().get("media_controller").preview_media_status_changed.emit()
```

### Files changed

- `openlp/core/ui/media/mediaplayer.py` — `media_status_changed_event()` only

### What is not changed

Live video playback, audio players, stream backgrounds, the looping UI button for non-background media.

---

## Fix 2 — Video Background Thumbnails

### Problem

Two places show a black placeholder instead of the video background:

- **Themes panel** — `ThemeManager.update_preview_images()` calls `Renderer.generate_preview()`, which calls `set_theme()` on a live-mode display. The `is_display=True` + `ServiceItemType.Text` branch overrides `background_type = 'video'` to `'transparent'`, so the webview background is transparent and `grab()` captures black.
- **Preview pane slide thumbnails** — `set_theme()` on a non-live `DisplayWindow` overrides `background_type = 'video'` to `'solid'` with the theme's border color.

### Solution

Extract a static frame from the video file once and store it on disk. Substitute it as an `image` background in all non-live contexts.

#### New module: `openlp/core/lib/videoframes.py`

**`extract_video_frame(video_path: Path, offset_ms: int = 1000) -> QImage | None`**

- Creates a `QMediaPlayer` + `QVideoSink` (no visible widget needed).
- Connects `mediaStatusChanged` to seek to `offset_ms` once `LoadedMedia` fires, then calls `play()`.
- Connects `QVideoSink.videoFrameChanged` to capture the first valid frame.
- Uses `wait_for()` (from `openlp.core.common.utils`) to spin the Qt event loop until a frame is captured, with a 5-second timeout.
- Calls `player.stop()` and returns the `QImage`. Returns `None` on timeout or failure.

**`get_video_preview_frame(theme) -> Path | None`**

- Builds the expected frame path: `AppLocation.get_section_data_path('themes') / theme.theme_name / 'preview_frame.png'`.
- If the file already exists, returns the path immediately.
- If not, calls `extract_video_frame(theme.background_filename)`, saves the result as PNG, returns the path.
- Returns `None` if extraction fails or `background_filename` is missing.

**`cache_video_preview_frame(theme) -> Path | None`**

- Like `get_video_preview_frame` but always re-extracts (used at save time to refresh the cache when the video file changes).

#### Call site 1: `openlp/core/ui/thememanager.py` — `save_theme()`

After the background file copy block (line ~754), add:

```python
if theme.background_type == 'video' and theme.background_filename:
    cache_video_preview_frame(theme)
```

This runs at theme save/import time so the frame is ready before any display.

#### Call site 2: `openlp/core/display/window.py` — `set_theme()` non-live branch

Replace the current solid-color override for video backgrounds:

```python
# Before (non-live branch)
if theme.background_type == 'stream' or theme.background_type == 'video':
    theme_copy.background_type = 'solid'
    ...

# After
if theme.background_type == 'stream':
    theme_copy.background_type = 'solid'
    ...
elif theme.background_type == 'video':
    frame_path = get_video_preview_frame(theme_copy)
    if frame_path:
        theme_copy.background_type = 'image'
        theme_copy.background_filename = frame_path
    else:
        theme_copy.background_type = 'solid'
        theme_copy.background_start_color = theme.background_border_color
        ...  # existing fallback unchanged
```

#### Call site 3: `openlp/core/display/render.py` — `generate_preview()`

Before calling `set_theme()`, substitute the theme copy for video backgrounds:

```python
def generate_preview(self, theme_data, force_page=False, generate_screenshot=True):
    theme_for_preview = copy.deepcopy(theme_data)
    if theme_for_preview.background_type == 'video':
        frame_path = get_video_preview_frame(theme_for_preview)
        if frame_path:
            theme_for_preview.background_type = 'image'
            theme_for_preview.background_filename = frame_path
    self.set_theme(theme_for_preview, is_sync=True, service_item_type=ServiceItemType.Text)
    ...
```

### Frame storage location

```
~/.local/share/openlp/themes/
└── {ThemeName}/
    ├── {ThemeName}.json
    ├── video_file.mp4        ← existing
    └── preview_frame.png     ← NEW, extracted at 1s
```

### Lazy fallback for existing themes

`get_video_preview_frame()` extracts on first call if the PNG is missing. This means existing video themes get their frame generated the first time the preview pane or theme thumbnail is rendered after the update — no migration step needed.

### Frame offset

1 second (`offset_ms=1000`). Skips fade-ins. Hardcoded — no user configuration.

### Error handling

- If the video file is missing or unreadable, `extract_video_frame` returns `None`.
- If `None`, all three call sites fall back to the existing behavior (transparent or solid).
- No crash path.

### Files changed

| File | Change |
|------|--------|
| `openlp/core/lib/videoframes.py` | New module |
| `openlp/core/ui/thememanager.py` | Call `cache_video_preview_frame` in `save_theme()` |
| `openlp/core/display/window.py` | Use frame as image background in non-live `set_theme()` |
| `openlp/core/display/render.py` | Substitute video → image before `generate_preview()` |

### What is not changed

Live display video playback, stream backgrounds, image/color themes, the existing thumbnail pipeline, Windows build/PyInstaller.

---

## Testing

- **Loop fix**: Run on Windows with a video background theme. Video should loop without black flash or pause.
- **Theme thumbnail**: After saving a video theme, the Themes panel thumbnail should show a still frame of the video with sample text on top.
- **Preview pane**: Selecting a service item that uses a video theme should show the frozen frame as the slide background in the preview thumbnails at the bottom of the pane.
- **Fallback**: Temporarily rename a theme's video file; preview and thumbnail should fall back to the solid color without crashing.
- **Existing themes**: On first launch after the update, existing video themes should auto-generate their frame without any user action.
