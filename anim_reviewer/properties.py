import bpy

from . import handlers
from .paths import TEMPORARY_OUTPUT_DIR


class VideoProperties(bpy.types.PropertyGroup):
    include_audio: bpy.props.BoolProperty(
        name="Include Audio",
        description="Include audio in the playblast video",
        default=True,
    )  # type: ignore

    codec: bpy.props.EnumProperty(
        name="Video Codec",
        description="Video codec for playblast",
        items=[
            ("libx264", "H.264", "H.264 codec"),
            ("libx265", "H.265", "H.265/HEVC codec"),
            ("mpeg4", "MPEG-4", "MPEG-4 codec"),
            ("libsvtav1", "AV1", "AV1 codec"),
        ],
        default="libx264",
    )  # type: ignore


class OverrideProperties(bpy.types.PropertyGroup):
    scale: bpy.props.IntProperty(
        name="Resolution Scale",
        description="Scale factor for the playblast resolution",
        subtype="PERCENTAGE",
        default=50,
        min=1,
        max=100,
    )  # type: ignore

    use_frame_range: bpy.props.BoolProperty(
        name="Use Frame Range",
        description=(
            "Use specific frame range for the playblast instead of the entire scene frame range\n"
            "If disabled, the playblast will use the scene's start and end frames"
        ),
        default=False,
    )  # type: ignore

    frame_start: bpy.props.IntProperty(
        name="Start Frame",
        description="Start frame for the playblast",
        default=1,
        min=0,
    )  # type: ignore

    frame_end: bpy.props.IntProperty(
        name="End Frame",
        description="End frame for the playblast",
        default=250,
        min=0,
    )  # type: ignore

    show_overlays: bpy.props.BoolProperty(
        name="Show Overlays",
        description="Show overlays like gizmos and outlines in the playblast",
        default=False,
    )  # type: ignore

    use_viewport_shading: bpy.props.BoolProperty(
        name="Use Viewport Shading",
        description=(
            "Use specific viewport shading mode for the playblast\n"
            "If disabled, the playblast will use the scene's viewport shading mode"
        ),
        default=False,
    )  # type: ignore

    viewport_shading: bpy.props.EnumProperty(
        name="Viewport Shading",
        description="Viewport shading mode for the playblast",
        items=[
            ("WIREFRAME", "", "Wireframe shading", "SHADING_WIRE", 1),
            ("SOLID", "", "Solid shading", "SHADING_SOLID", 2),
            ("MATERIAL", "", "Material shading", "SHADING_TEXTURE", 3),
            ("RENDERED", "", "Rendered shading", "SHADING_RENDERED", 4),
        ],
        default="MATERIAL",
    )  # type: ignore


def get_version_str(self):
    if not self.use_version:
        return ""
    return f"v{self.version:03d}"


def get_full_path(self):
    dir = self.directory
    name = self.name
    use_ver = self.use_version
    ver = self.version_str
    ext = self.extension

    if not dir:
        dir = bpy.path.abspath("//")
    else:
        dir = bpy.path.abspath(dir)

    if not dir:
        dir = TEMPORARY_OUTPUT_DIR.as_posix()

    dir = dir.replace("\\", "/")
    if not dir.endswith("/"):
        dir += "/"

    if use_ver:
        ver = "." + ver

    path = f"{dir}{name}{ver}{ext}"

    return path


class FileProperties(bpy.types.PropertyGroup):
    directory: bpy.props.StringProperty(
        name="Directory",
        description="Directory to save the playblast file. \n"
        "Defaults to the current blend file's directory (`//`). \n"
        "If the blend file is not saved, a temporary directory will be used instead.",
        subtype="DIR_PATH",
        options={"PATH_SUPPORTS_BLEND_RELATIVE"}
        if bpy.app.version >= (4, 5)
        else set(),
        default="//",
    )  # type: ignore

    name: bpy.props.StringProperty(
        name="File Name",
        description="Base name for playblast file",
        default="playblast",
    )  # type: ignore

    use_version: bpy.props.BoolProperty(
        name="Use Version",
        description="",
        default=True,
    )  # type: ignore

    version: bpy.props.IntProperty(
        name="Version",
        description="Version number for the playblast file",
        default=1,
        min=0,
    )  # type: ignore

    extension: bpy.props.EnumProperty(
        name="Extension",
        description="File extension for playblast",
        items=[
            (".mp4", ".mp4", "MP4 format"),
            (".mov", ".mov", "MOV format"),
            (".avi", ".avi", "AVI format"),
            (".mkv", ".mkv", "MKV format"),
        ],
        default=".mp4",
    )  # type: ignore

    version_str: bpy.props.StringProperty(
        name="Version String",
        description="Read-only properties.\n"
        "Get version string from the version number."
        "If version is 1, return v001."
        "Else return empty string.",
        get=get_version_str,
    )  # type: ignore

    full_path: bpy.props.StringProperty(
        name="Full Path",
        description="Read-only properties.\n"
        "Join all parts to get the full path of the playblast file.",
        get=get_full_path,
    )  # type: ignore


def burn_in_preview_update(self, context):
    if self.enable and self.preview:
        handlers.register_or_unregister_preview_handler("register")
    else:
        handlers.register_or_unregister_preview_handler("unregister")


class BurnInProperties(bpy.types.PropertyGroup):
    enable: bpy.props.BoolProperty(
        name="Enable Burn-In Data",
        description="Enable burn-in text overlay on the playblast.",
        default=False,
        update=burn_in_preview_update,
    )  # type: ignore

    preview: bpy.props.BoolProperty(
        name="Preview in Viewport",
        description="Preview the burn-in text in the 3D viewport\n"
        "You need to be in Camera view to see it",
        default=True,
        update=burn_in_preview_update,
    )  # type: ignore

    font_family: bpy.props.StringProperty(
        name="Font Family",
        description="Font family for the burn-in text",
        subtype="FILE_PATH",
        default="",
    )  # type: ignore

    font_size: bpy.props.IntProperty(
        name="Font Size",
        description="Size of the burn-in text font",
        default=40,
    )  # type: ignore

    margin: bpy.props.IntProperty(
        name="Margin",
        description="Text margin from the edges of the viewport",
        default=10,
    )  # type: ignore

    color: bpy.props.FloatVectorProperty(
        name="Color",
        description="Color of the burn-in text",
        subtype="COLOR",
        size=4,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0, 1.0),
    )  # type: ignore

    top_left: bpy.props.StringProperty(
        name="Top Left",
        description="Text to display in the top left corner",
        default=r"File: {file_name} {file_version}",
    )  # type: ignore

    top_center: bpy.props.StringProperty(
        name="Top Center",
        description="Text to display in the top center",
        default=r"",
    )  # type: ignore

    top_right: bpy.props.StringProperty(
        name="Top Right",
        description="Text to display in the top right corner",
        default=r"Date: {datetime}",
    )  # type: ignore

    bottom_left: bpy.props.StringProperty(
        name="Bottom Left",
        description="Text to display in the bottom left corner",
        default=r"Resolution: {width}x{height}",
    )  # type: ignore

    bottom_center: bpy.props.StringProperty(
        name="Bottom Center",
        description="Text to display in the bottom center",
        default=r"Camera: {camera_name} {camera_focal}mm",
    )  # type: ignore

    bottom_right: bpy.props.StringProperty(
        name="Bottom Right",
        description="Text to display in the bottom right corner",
        default=r"Frame: {frame_current} | {frame_start}-{frame_end} | {frame_rate} fps",
    )  # type: ignore


class AnimReviewerProperties(bpy.types.PropertyGroup):
    video: bpy.props.PointerProperty(type=VideoProperties)  # type: ignore
    override: bpy.props.PointerProperty(type=OverrideProperties)  # type: ignore
    file: bpy.props.PointerProperty(type=FileProperties)  # type: ignore
    burn_in: bpy.props.PointerProperty(type=BurnInProperties)  # type: ignore


classes = (
    VideoProperties,
    OverrideProperties,
    FileProperties,
    BurnInProperties,
    AnimReviewerProperties,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.anim_reviewer = bpy.props.PointerProperty(
        type=AnimReviewerProperties
    )


def unregister():
    del bpy.types.Scene.anim_reviewer

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
