import functools
import logging
import os
import re
from collections import defaultdict
from datetime import datetime
from typing import TypedDict

import bpy

logger = logging.getLogger(__name__)

ALL_PLACEHOLDER_PATTERN = re.compile(r"\{([^}]+)\}")
BPY_EXPR_PATTERN = re.compile(r"\{bpy\.[^}!:{]*(?:![^}:]*)?(?::[^}]*)?\}")

BURN_IN_POSITIONS = [
    "top_left",
    "top_center",
    "top_right",
    "bottom_left",
    "bottom_center",
    "bottom_right",
]

META_DATA_DESCRIPTIONS = {
    "blender_name": "Name of the current Blender file",
    "blender_path": "Full path of the current Blender file",
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


class MetaData(TypedDict):
    """The metadata used to replace the placeholders for burn-in text."""

    blender_name: str
    blender_path: str
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


@functools.lru_cache(maxsize=128)
def _sanitize_bpy_key(expr: str) -> str:
    """Sanitize a bpy expression into a valid format_map key.

    ``bpy.data.objects[\"Cube\"].location[0]`` -> ``bpy_data_objects(Cube)_location(0)``
    """
    s = expr.replace(".", "_")
    s = s.replace("[", "(")
    s = s.replace("]", ")")
    s = s.replace('"', "")
    s = s.replace("'", "")
    return s


def find_first_burn_in_error(text: str) -> tuple[str, str] | None:
    """Find the first invalid placeholder in burn-in text.

    Returns ``(placeholder, error_msg)`` or ``None`` if all valid.
    """
    if not text:
        return None

    for match in ALL_PLACEHOLDER_PATTERN.finditer(text):
        inner = match.group(1)
        if inner.startswith("bpy."):
            expr = inner.split("!")[0].split(":")[0]
            try:
                eval(expr, {"bpy": bpy})
            except Exception as e:
                return (f"{{{inner}}}", str(e))
        else:
            key = inner.split("!")[0].split(":")[0]
            if key not in META_DATA_DESCRIPTIONS:
                return (f"{{{inner}}}", f"Unknown variable: {key}")

    return None


def get_bpy_rna_values(context: bpy.types.Context) -> dict:
    """Extract and evaluate all {bpy.xxx} RNA expressions from burn-in text fields.

    Returns a dict of {sanitized_key: value}, or empty dict if burn-in is
    disabled or no expressions are found.
    """
    burn_in = context.scene.anim_reviewer.burn_in
    if not burn_in.enable:
        return {}

    expressions = set()
    for pos in BURN_IN_POSITIONS:
        for match in BPY_EXPR_PATTERN.finditer(getattr(burn_in, pos)):
            raw = match.group()[1:-1]
            expr = raw.split("!")[0].split(":")[0]
            expressions.add(expr)

    if not expressions:
        return {}

    result = {}
    for expr in expressions:
        try:
            value = eval(expr, {"bpy": bpy})
            if isinstance(value, float):
                value = round(value, 2)
            result[_sanitize_bpy_key(expr)] = value
        except Exception as e:
            logger.warning('Failed to evaluate burn-in expression "%s": %s', expr, e)
            result[_sanitize_bpy_key(expr)] = ""
    return result


def resolve_text(text: str, metadata: defaultdict) -> str:
    """Replace {bpy.xxx} expressions and standard metadata placeholders in text.

    {bpy.xxx} patterns are first transformed to use sanitized keys, then
    standard format_map resolves all placeholders against the metadata dict.
    """

    def _replacer(match):
        inner = match.group()[1:-1]
        conv = ""
        fmt = ""
        rest = inner
        if "!" in rest:
            expr, _, rest = rest.partition("!")
            conv, _, fmt = rest.partition(":")
            conv = "!" + conv
            if fmt:
                fmt = ":" + fmt
        elif ":" in rest:
            expr, _, fmt = rest.partition(":")
            fmt = ":" + fmt
        else:
            expr = rest
        return "{" + _sanitize_bpy_key(expr) + conv + fmt + "}"

    text = BPY_EXPR_PATTERN.sub(_replacer, text)
    return text.format_map(metadata)


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

    # Get current Blender file name
    blender_file_path = bpy.data.filepath
    if blender_file_path:
        blender_name = os.path.splitext(os.path.basename(blender_file_path))[0]
    else:
        blender_name = "Untitled"

    metadata: MetaData = {
        "blender_name": blender_name,
        "blender_path": blender_file_path,
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

    metadata.update(get_bpy_rna_values(context))

    return defaultdict(str, metadata)
