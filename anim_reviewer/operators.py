import json
import os
import shutil
import subprocess
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

import bpy
from bl_operators.presets import AddPresetBase
from bpy.app.translations import pgettext_rpt as rpt_
from bpy_extras.io_utils import ExportHelper, ImportHelper

from .metadata import get_metadata
from .paths import BFONT_PATH, TEMPLATE_ASS_PATH
from .utils import detect_ffmpeg, get_full_font_name, play_video


@contextmanager
def render_properties_override(context: bpy.types.Context):
    """Context manager for overriding render properties during playblast"""

    scene = context.scene
    render = scene.render
    anim_reviewer = scene.anim_reviewer
    metadata = get_metadata(context)

    space = context.space_data
    region = space.region_3d

    # Store original render properties
    resolution_x = render.resolution_x
    resolution_y = render.resolution_y
    resolution_percentage = render.resolution_percentage

    frame_current = scene.frame_current
    frame_start = scene.frame_start
    frame_end = scene.frame_end
    use_preview_range = scene.use_preview_range

    filepath = render.filepath
    use_file_extension = render.use_file_extension
    use_render_cache = render.use_render_cache
    file_format = render.image_settings.file_format
    color_mode = render.image_settings.color_mode
    color_depth = render.image_settings.color_depth
    compression = render.image_settings.compression
    multiview = render.use_multiview

    shading_type = space.shading.type
    show_xray = space.shading.show_xray
    show_overlays = space.overlay.show_overlays

    # Setup render properties for playblast
    render.resolution_x = metadata["width"]
    render.resolution_y = metadata["height"]
    render.resolution_percentage = 100

    # Use scene frame range instead of preview range
    # Audio range will always use scene frame range
    if anim_reviewer.override.use_frame_range:
        scene.use_preview_range = False
        scene.frame_start = anim_reviewer.override.frame_start
        scene.frame_end = anim_reviewer.override.frame_end
    elif scene.use_preview_range:
        scene.frame_start = scene.frame_preview_start
        scene.frame_end = scene.frame_preview_end

    render.use_file_extension = True
    render.use_render_cache = False
    render.image_settings.file_format = "PNG"
    render.image_settings.color_mode = "RGB"
    render.image_settings.color_depth = "8"
    render.image_settings.compression = 15
    render.use_multiview = False

    if anim_reviewer.override.use_viewport_shading:
        space.shading.type = anim_reviewer.override.viewport_shading
    space.shading.show_xray = False
    space.overlay.show_overlays = anim_reviewer.override.show_overlays

    try:
        # Ensure the VIEW_3D area is in camera view
        region.view_perspective = "CAMERA"

        yield
    finally:
        # Restore original render properties
        render.resolution_x = resolution_x
        render.resolution_y = resolution_y
        render.resolution_percentage = resolution_percentage

        scene.frame_set(frame_current)
        scene.frame_start = frame_start
        scene.frame_end = frame_end
        scene.use_preview_range = use_preview_range

        render.filepath = filepath
        render.use_file_extension = use_file_extension
        render.use_render_cache = use_render_cache
        render.image_settings.file_format = file_format
        render.image_settings.color_mode = color_mode
        render.image_settings.color_depth = color_depth
        render.image_settings.compression = compression
        render.use_multiview = multiview

        space.shading.type = shading_type
        space.shading.show_xray = show_xray
        space.overlay.show_overlays = show_overlays


@contextmanager
def register_collect_metadata_handler(context: bpy.types.Context):
    """Register a handler to collect metadata durning playblast.

    The collected metadata will temporarily stored in `scene.anim_reviewer["metadata"]`.
    """

    def handler(scene: bpy.types.Scene):
        metadata = get_metadata(bpy.context, is_rendering=True)
        scene.anim_reviewer["metadata"][str(scene.frame_current)] = metadata

    context.scene.anim_reviewer["metadata"] = {}
    bpy.app.handlers.frame_change_post.append(handler)

    try:
        yield
    finally:
        bpy.app.handlers.frame_change_post.remove(handler)
        del context.scene.anim_reviewer["metadata"]


class ANIM_REVIEWER_OT_run(bpy.types.Operator):
    bl_idname = "render.anim_review"
    bl_label = "Run Anim Review"
    bl_description = (
        "Create a playblast video of the current scene.\n"
        "Please ensure you have an active camera and ffmpeg is installed in your system."
    )

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return context.area.type == "VIEW_3D" and context.scene.camera is not None

    def execute(self, context: bpy.types.Context):
        # First detect whether ffmpeg is installed
        if not detect_ffmpeg():
            self.report(
                {"ERROR"},
                "FFmpeg is not installed or not found in PATH.",
            )
            return {"CANCELLED"}

        with (
            TemporaryDirectory(prefix="blender_anim_reviewer_") as temp_dir,
            render_properties_override(context),
            register_collect_metadata_handler(context),
        ):
            self.temp_dir = Path(temp_dir)
            self.temp_png = self.temp_dir / "%04d.png"
            self.temp_sub = self.temp_dir / "subtitle.ass"
            self.temp_aud = self.temp_dir / "audio.mp3"
            self.temp_font = self.copy_font_to_temp(context)

            # Use OpenGL render to render frames
            context.scene.render.filepath = self.temp_dir.as_posix() + "/"
            bpy.ops.render.opengl(animation=True, view_context=True)

            # Keep datetime for each frame is the same
            t = datetime.now().isoformat(sep=" ", timespec="seconds")
            for data in context.scene.anim_reviewer["metadata"].values():
                data["datetime"] = t

            # Get real frame range
            if context.scene.use_preview_range:
                self.frame_start = context.scene.frame_preview_start
                self.frame_end = context.scene.frame_preview_end
            else:
                self.frame_start = context.scene.frame_start
                self.frame_end = context.scene.frame_end

            self.build_subtitles(context)
            self.build_audio(context)
            self.build_video(context)

        return {"FINISHED"}

    def copy_font_to_temp(self, context: bpy.types.Context) -> Path:
        """Copy the specified font to temporary directory for ffmpeg usage.

        This can avoid many error logs for ffmpeg.
        """
        font_path: Path = context.scene.anim_reviewer.burn_in.font_family
        if not font_path or not os.path.exists(font_path):
            font_path = BFONT_PATH
        else:
            font_path = Path(font_path)

        temp_font = Path(self.temp_dir, "font", font_path.name)
        temp_font.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(font_path, temp_font)
        return temp_font

    def build_subtitles(self, context: bpy.types.Context):
        """Build subtitles of metadata for the video."""

        def frame_to_timecode(frame, fps):
            """Convert frame number to ASS timecode format (H:MM:SS.cs)."""
            total_seconds = frame / fps
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            seconds = total_seconds % 60

            if frame != 0:
                seconds -= 0.01

            # ASS uses centiseconds (0.01s) for the fractional part
            return f"{hours}:{minutes:02d}:{seconds:06.2f}"

        def get_hex_color(color):
            """Get the color hex code that used in ASS subtitles."""
            color = list(color)

            # # Convert scene linear to srgb
            # color[0:3] = list(mathutils.Color(color[:3]).from_scene_linear_to_srgb())

            # ASS Subtitle use reversed alpha channel
            color[3] = 1 - color[3]

            # ASS Subtitle use reversed order, it is AABBGGRR
            color.reverse()

            for i, c in enumerate(color):
                # Convert color from 0~1 to 0~255
                cc = int(round(c * 255))

                # Convert color from dec to hex
                color[i] = f"{cc:02X}"

            return "".join(["&H", *color])

        scene = context.scene
        anim_reviewer = scene.anim_reviewer

        if not anim_reviewer.burn_in.enable:
            return

        with open(TEMPLATE_ASS_PATH, "r", encoding="utf-8") as f:
            template_ass = f.read()

        res_x = scene.render.resolution_x
        res_y = scene.render.resolution_y
        fps = scene.render.fps

        # Get real name of font
        font_name = get_full_font_name(self.temp_font)

        # Keep text ratio regardless of resolution scale
        font_size = (
            anim_reviewer.burn_in.font_size * anim_reviewer.override.scale // 100
        )

        # Get correct color format
        font_color = get_hex_color(anim_reviewer.burn_in.color)

        subtitles = template_ass.format_map(
            {
                "res_x": res_x,
                "res_y": res_y,
                "font_name": font_name,
                "font_size": font_size,
                "font_color": font_color,
            }
        )

        # Also scale margin to keep aspect ratio
        margin = anim_reviewer.burn_in.margin * anim_reviewer.override.scale // 100

        # Notice that the origin (0,0) is at the top-left corner for ass subtitles
        # pos, align, x, y
        vars = [
            (
                "top_left",
                "7",
                margin,
                margin,
            ),
            (
                "top_center",
                "8",
                res_x // 2,
                margin,
            ),
            (
                "top_right",
                "9",
                res_x - margin,
                margin,
            ),
            (
                "bottom_left",
                "1",
                margin,
                res_y - margin,
            ),
            (
                "bottom_center",
                "2",
                res_x // 2,
                res_y - margin,
            ),
            (
                "bottom_right",
                "3",
                res_x - margin,
                res_y - margin,
            ),
        ]

        dialogues = []
        template_dialogue = "Dialogue: 0,{start},{end},default,,0,0,0,,{{\\an{align}\\pos({x},{y})}}{text}"
        for frame in range(self.frame_start, self.frame_end + 1):
            metadata = scene.anim_reviewer["metadata"][str(frame)]
            start = frame_to_timecode(frame - self.frame_start, fps)
            end = frame_to_timecode(frame - self.frame_start + 1, fps)

            for pos, align, x, y in vars:
                text = getattr(anim_reviewer.burn_in, pos)
                try:
                    text = text.format_map(metadata)
                except Exception:
                    self.report(f'Error burn in text in {pos}: "{text}"')
                    continue

                dialogue = template_dialogue.format(
                    start=start,
                    end=end,
                    align=align,
                    x=x,
                    y=y,
                    text=text,
                )
                dialogues.append(dialogue)

        subtitles += "\n".join(dialogues)

        # Save subtitles to temporary folder
        with open(self.temp_sub, "w", encoding="utf-8") as f:
            f.write(subtitles)

    def build_audio(self, context: bpy.types.Context):
        """Build audio file use blender's built-in tools."""

        if not context.scene.anim_reviewer.video.include_audio:
            return

        # Render audio
        bpy.ops.sound.mixdown(
            filepath=self.temp_aud.as_posix(),
            container="MP3",
            codec="MP3",
        )

    def build_video(self, context: bpy.types.Context):
        """Build video from the rendered frames using ffmpeg."""

        anim_reviewer = context.scene.anim_reviewer
        output_path = anim_reviewer.file.full_path
        codec = anim_reviewer.video.codec
        include_audio = anim_reviewer.video.include_audio
        enable_burn_in = anim_reviewer.burn_in.enable

        # Get crf for different codecs
        match codec:
            case "libx264":
                crf = 23
            case "libx265":
                crf = 28
            case "mpeg4":
                crf = 5
            case "libsvtav1":
                crf = 35
            case _:
                crf = 23

        escape_font_path = self.temp_font.parent.as_posix().replace(":", "\\:")
        escape_sub_path = self.temp_sub.as_posix().replace(":", "\\:")

        # Ensure output path exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        ffmpeg_cmd = (
            "ffmpeg " +
            "-y " +
            f"-framerate {context.scene.render.fps} " +
            f"-start_number {self.frame_start} " +
            f'-i "{self.temp_png.as_posix()}" ' +
            (f'-i "{self.temp_aud.as_posix()}" ' if include_audio else "") +
            f"-c:v {codec} " +
            ("-c:a copy " if include_audio else "") +
            "-map 0:v:0 " +
            ("-map 1:a:0 " if include_audio else "") +
            f"-crf {crf} " +
            "-pix_fmt yuv420p " +
            f"-frames:v {self.frame_end - self.frame_start + 1} " +
            (f"-vf \"subtitles='{escape_sub_path}':fontsdir='{escape_font_path}'\" " if enable_burn_in else "") +
            f'"{output_path}"'
        )  # fmt: skip

        try:
            print("Executing command:", ffmpeg_cmd)
            subprocess.run(ffmpeg_cmd, shell=True, check=True)
            self.report(
                {"INFO"},
                rpt_(
                    msgid='Playblast completed, saved to "{}", opening video...'
                ).format(output_path),
            )

            play_video(output_path)

            if os.environ.get("OCIO") and bpy.app.version < (5, 0):
                self.report(
                    {"WARNING"},
                    rpt_(
                        "OCIO environment variable detected. Video playback may crash on Blender versions before 5.0\n"
                        "If you encounter a crash, please try to unset OCIO environment variable or upgrade to Blender 5.0 or later."
                    ),
                )
        except subprocess.CalledProcessError:
            self.report(
                {"ERROR"},
                "FFmpeg processing failed, please open console for details.",
            )
            return


class ANIM_REVIEWER_OT_import_settings(bpy.types.Operator, ImportHelper):
    bl_idname = "anim_reviewer.import_settings"
    bl_label = "Import Settings"
    bl_description = "Import Anim Reviewer settings from a file"

    filename_ext = ".json"
    filter_glob: bpy.props.StringProperty(default="*.json", options={"HIDDEN"})

    def execute(self, context):
        anim_reviewer = context.scene.anim_reviewer
        with open(self.filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Reuse the same data structure as preset
        for attr, value in data.items():
            _, prop_group, prop_name = attr.split(".")
            prop = getattr(anim_reviewer, prop_group)

            # Convert list back to color property
            if isinstance(getattr(prop, prop_name), bpy.types.bpy_prop_array):
                value = tuple(value)

            setattr(prop, prop_name, value)

        return {"FINISHED"}


class ANIM_REVIEWER_OT_export_settings(bpy.types.Operator, ExportHelper):
    bl_idname = "anim_reviewer.export_settings"
    bl_label = "Export Settings"
    bl_description = "Export current Anim Reviewer settings to a file"

    filename_ext = ".json"
    filter_glob: bpy.props.StringProperty(default="*.json", options={"HIDDEN"})

    def execute(self, context: bpy.types.Context):
        anim_reviewer = context.scene.anim_reviewer

        # Reuse the same data structure as preset
        data = {}
        for attr in ANIM_REVIEWER_OT_preset_add.preset_values:
            _, prop_group, prop_name = attr.split(".")
            value = getattr(getattr(anim_reviewer, prop_group), prop_name)

            # Convert color to list for json serialization
            if isinstance(value, bpy.types.bpy_prop_array):
                value = list(value)

            data[attr] = value

        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        return {"FINISHED"}


class ANIM_REVIEWER_OT_preset_add(AddPresetBase, bpy.types.Operator):
    """Add a Anim Reviewer Preset"""

    bl_idname = "anim_reviewer.preset_add"
    bl_label = "Add Anim Reviewer Preset"
    preset_menu = "ANIM_REVIEWER_PT_presets"
    preset_subdir = "anim_reviewer"

    preset_defines = [
        "anim_reviewer = bpy.context.scene.anim_reviewer",
    ]

    preset_values = [
        "anim_reviewer.video.include_audio",
        "anim_reviewer.video.codec",
        "anim_reviewer.override.scale",
        "anim_reviewer.override.show_overlays",
        "anim_reviewer.override.use_viewport_shading",
        "anim_reviewer.override.viewport_shading",
        "anim_reviewer.file.directory",
        "anim_reviewer.file.name",
        "anim_reviewer.file.use_version",
        "anim_reviewer.file.extension",
        "anim_reviewer.burn_in.enable",
        "anim_reviewer.burn_in.preview",
        "anim_reviewer.burn_in.font_family",
        "anim_reviewer.burn_in.font_size",
        "anim_reviewer.burn_in.margin",
        "anim_reviewer.burn_in.color",
        "anim_reviewer.burn_in.top_left",
        "anim_reviewer.burn_in.top_center",
        "anim_reviewer.burn_in.top_right",
        "anim_reviewer.burn_in.bottom_left",
        "anim_reviewer.burn_in.bottom_center",
        "anim_reviewer.burn_in.bottom_right",
    ]


classes = (
    ANIM_REVIEWER_OT_run,
    ANIM_REVIEWER_OT_import_settings,
    ANIM_REVIEWER_OT_export_settings,
    ANIM_REVIEWER_OT_preset_add,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
