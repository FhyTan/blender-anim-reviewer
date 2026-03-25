# Changelog

## 1.0.1

- Modified the logic for detecting whether `ffmpeg` is installed; fixes an issue where `ffmpeg` was not detected on macOS.
- Fixed startup issues for the player on non-Windows platforms.
- Added a warning: when using an OCIO configuration on Blender versions below 5.0, the built-in player may crash; the program will now display a warning to the user.
