import os
from collections import defaultdict
from datetime import datetime
from typing import TypedDict

import bpy


class MetaData(TypedDict):
    """The metadata used to replace the placeholders for burn-in text."""

    datetime: str
    width: int
    height: int
    file_name: str
    file_version: str
    file_ext: str
    file_full_name: str
    frame_current: int
    frame_start: int
    frame_end: int
    frame_rate: int
    camera_name: str
    camera_focal: float
    camera_sensor_width: float
    camera_sensor_height: float


META_DATA_DESCRIPTIONS = {
    "datetime": "Current date and time",
    "width": "Playblast width in pixels",
    "height": "Playblast height in pixels",
    "file_name": "Name of the output file without extension",
    "file_version": "Version string of the output file",
    "file_ext": "File extension of the output file",
    "file_full_name": "Full name of the output file with extension",
    "frame_current": "Current frame number",
    "frame_start": "Start frame of the playblast",
    "frame_end": "End frame of the playblast",
    "frame_rate": "Frame rate of the playblast",
    "camera_name": "Name of the active camera",
    "camera_focal": "Focal length of the active camera in mm",
    "camera_sensor_width": "Sensor width of the active camera in mm",
    "camera_sensor_height": "Sensor height of the active camera in mm",
}


def get_metadata(context: bpy.types.Context, is_rendering: bool = False) -> MetaData:
    """Get the metadata for current frame in the given context."""

    scene = context.scene
    render = scene.render
    anim_reviewer = scene.anim_reviewer

    # Get Resolution Info
    if is_rendering:
        # When rendering, the resolution already changed to the render size
        res_x = render.resolution_x
        res_y = render.resolution_y
    else:
        # When not rendering, calculate the resolution with scale and make sure it's even
        scale = anim_reviewer.override.scale

        res_x = int(render.resolution_x * scale / 100)
        res_y = int(render.resolution_y * scale / 100)

        res_x += res_x % 2
        res_y += res_y % 2

    # Get frame range info
    if anim_reviewer.override.use_frame_range:
        frame_start = anim_reviewer.override.frame_start
        frame_end = anim_reviewer.override.frame_end
    elif scene.use_preview_range:
        frame_start = scene.frame_preview_start
        frame_end = scene.frame_preview_end
    else:
        frame_start = scene.frame_start
        frame_end = scene.frame_end

    # Get camera info
    camera = scene.camera
    if camera and camera.type == "CAMERA":
        camera_focal = f"{camera.data.lens:.2f}"
        camera_name = camera.name
        camera_sensor_width = f"{camera.data.sensor_width:.1f}"
        camera_sensor_height = f"{camera.data.sensor_height:.1f}"
    else:
        camera_focal = ""
        camera_name = ""
        camera_sensor_width = ""
        camera_sensor_height = ""

    metadata: MetaData = {
        "datetime": datetime.now().isoformat(sep=" ", timespec="seconds"),
        "width": res_x,
        "height": res_y,
        "file_name": anim_reviewer.file.name,
        "file_version": anim_reviewer.file.version_str,
        "file_ext": anim_reviewer.file.extension,
        "file_full_name": os.path.basename(anim_reviewer.file.full_path),
        "frame_current": scene.frame_current,
        "frame_start": frame_start,
        "frame_end": frame_end,
        "frame_rate": int(render.fps),
        "camera_name": camera_name,
        "camera_focal": camera_focal,
        "camera_sensor_width": camera_sensor_width,
        "camera_sensor_height": camera_sensor_height,
    }

    return defaultdict(str, metadata)
