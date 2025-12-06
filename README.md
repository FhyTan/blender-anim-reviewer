[English](README.md) | [中文](README.zh-CN.md)

# Enhanced Blender Playblast Review Plugin

This plugin enhances Blender's native playblast, providing convenient features that allow one-click animation preview, temporary modification of video properties, and easy addition of custom information to videos.

You can install it from official extension website:
<https://extensions.blender.org/add-ons/anim-reviewer/>

![demonstrate](images/demonstrate.gif)

## System Requirements

- Blender 4.2.0 or higher
- FFmpeg (required for video processing)

Due to some limitations of the Blender Python API, using this plugin requires FFmpeg to be installed on your computer first for video processing and compositing.

If you are using Windows, we recommend using [UniGetUI](https://github.com/marticliment/UniGetUI) to quickly install FFmpeg.

## Location

3D Viewport ‣ N-panel ‣ Tool ‣ Anim Reviewer

![interface](images/interface.png)

## Usage Tutorial

Ensure there is an active camera in the scene, go to the Anim Reviewer panel and click "Run Anim Review" to start playblast.

## Feature Overview

### Basic Playblast

- One-click generation of current scene preview videos
- Support for multiple video codec formats (H.264, H.265, MPEG-4, AV1)
- Can synchronously output audio
- Modify video parameters (resolution, frame range, output location, etc.) without affecting the scene settings, only take effect during playblast

### Burn-in Metadata

- Overlay custom information on videos
- Support for 6 positions: top-left, top-center, top-right, bottom-left, bottom-center, bottom-right
- Display scene information, timestamps, frame numbers and other metadata
- Support for custom fonts, colors, sizes and margins

### Settings Management

- Use preset panels to easily switch between different settings
- Import/export settings files for easy team sharing

## Line Breaks

If your overlay information needs line breaks, you can use `\N` to represent line breaks. Although you can't see the effect in the Viewport (Blender text drawing doesn't support line breaks), it will work in the actual video.

![newline](images/newline.png)

## Contributing

If you have additional video format or video metadata requirements, or other feature requests, feel free to submit Issues and Pull Requests!
