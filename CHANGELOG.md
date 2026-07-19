# Changelog

## 1.1.1

- Fixed an error for `Run Anim Review` operator in Blender 5.2 due this official commit: <https://projects.blender.org/blender/blender/commit/4ecb84f7bd588c121f7ae701315dbc4a800be72e>

## 1.1.0

- Added `{camera_sensor_width}` and `{camera_sensor_height}` metadata variables for burn-in text.
- Added support for `{bpy.xxx}` RNA data path expressions in burn-in text (e.g. `{bpy.data.objects["Cube"].location[0]}`).
- Added validation for burn-in text placeholders — invalid or non-existent variables now show an inline error in the UI panel and gracefully fall back to empty string during render/preview.

## 1.0.3

- Fixed a crash when running playblast with the output media type set to video in Blender versions above 5.0.

## 1.0.2

- Auto-detect the area used for playblast, allowing you to call `bpy.ops.render.anim_review()` directly from the script editor.
- Add the `launch_player` parameter to the playblast operator to prevent the player from opening during batch scripts.

## 1.0.1

- Modified the logic for detecting whether `ffmpeg` is installed; fixes an issue where `ffmpeg` was not detected on macOS.
- Fixed startup issues for the player on non-Windows platforms.
- Added a warning: when using an OCIO configuration on Blender versions below 5.0, the built-in player may crash; the program will now display a warning to the user.
