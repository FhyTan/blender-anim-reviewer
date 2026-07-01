import logging
import os
from functools import partial
from pathlib import Path
from typing import List, Literal, Tuple

import blf
import bpy
import gpu
from bpy_extras.view3d_utils import location_3d_to_region_2d
from gpu_extras.batch import batch_for_shader

from .metadata import get_metadata, resolve_text
from .paths import BFONT_PATH

logger = logging.getLogger(__name__)


def preview_burn_in_handler():
    """Handler to draw burn-in text on the viewport to preview burn-in effect."""

    def poll(context: bpy.types.Context) -> bool:
        """Check if the current context is valid for drawing burn-in text"""
        return (
            context.area is not None
            and context.area.type == "VIEW_3D"
            and context.space_data is not None
            and context.space_data.region_3d is not None
            and context.space_data.region_3d.view_perspective == "CAMERA"
            and context.scene is not None
            and context.scene.camera is not None
        )

    def get_camera_frame_rect(
        context: bpy.types.Context,
    ) -> List[Tuple[float, float]]:
        """Get the rectangle of the camera frame in 3d viewport

        Returns:
            List of 4 tuples, each tuple is (x, y) coordinate of the rectangle corners
            in the order of top_right, bottom_right, bottom_left, top_left.

            Notice that the origin (0,0) is at the bottom-left corner of the viewport.
        """

        region = context.region
        rv3d = context.space_data.region_3d
        cam = context.scene.camera
        if cam is None:
            raise Exception("No camera found in the scene")

        # Get the camera frame corners in world space
        frame_corners = cam.data.view_frame(scene=context.scene)
        frame_corners_world = [cam.matrix_world @ corner for corner in frame_corners]

        # Convert the world space corners to 2D screen space
        frame_corners_2d = []
        for corner in frame_corners_world:
            corner_2d = location_3d_to_region_2d(region, rv3d, corner)
            frame_corners_2d.append(corner_2d)

        return frame_corners_2d

    def draw_rect(corners: List[Tuple[float, float]]):
        """Draw a rectangle in the viewport for debugging"""
        shader = gpu.shader.from_builtin("UNIFORM_COLOR")
        shader.uniform_float("color", (0, 0.5, 0.5, 1.0))
        batch = batch_for_shader(
            shader,
            "LINES",
            {
                "pos": corners,
            },
            indices=((0, 1), (1, 2), (2, 3), (3, 0)),
        )
        batch.draw(shader)

    context = bpy.context

    if not poll(context):
        return

    anim_reviewer = context.scene.anim_reviewer
    res_x = context.scene.render.resolution_x
    top_right, bottom_right, bottom_left, top_left = get_camera_frame_rect(context)
    metadata = get_metadata(context)

    # Calculate the scale factor to fit the text in the camera frame
    factor = (bottom_right[0] - bottom_left[0]) / res_x

    # Get font properties
    font_path = anim_reviewer.burn_in.font_family
    if not font_path or not os.path.exists(font_path):
        font_path = BFONT_PATH
    else:
        font_path = Path(font_path)
    font_id = blf.load(font_path.as_posix())
    font_size = int(anim_reviewer.burn_in.font_size * factor)
    font_color = anim_reviewer.burn_in.color
    font_margin = int(anim_reviewer.burn_in.margin * factor)

    blf.size(font_id, font_size)
    blf.color(font_id, *font_color)
    blf.enable(font_id, blf.SHADOW)
    blf.shadow(font_id, 6, 0, 0, 0, 1)

    # Calculate baseline height
    # Reference: https://blender.stackexchange.com/questions/312413/blf-module-how-to-draw-text-in-the-center
    full_height = blf.dimensions(font_id, "GJKLPgjklp!?")[1]
    word_height = blf.dimensions(font_id, "x")[1]
    base_height = (full_height - word_height) // 2

    positions = [
        (
            "top_left",
            lambda w: (
                top_left[0] + font_margin,
                top_left[1] - full_height - font_margin + base_height,
            ),
        ),
        (
            "top_center",
            lambda w: (
                (top_left[0] + top_right[0]) / 2 - w / 2,
                top_right[1] - full_height - font_margin + base_height,
            ),
        ),
        (
            "top_right",
            lambda w: (
                top_right[0] - w - font_margin,
                top_right[1] - full_height - font_margin + base_height,
            ),
        ),
        (
            "bottom_left",
            lambda w: (
                bottom_left[0] + font_margin,
                bottom_left[1] + font_margin + base_height,
            ),
        ),
        (
            "bottom_center",
            lambda w: (
                (bottom_left[0] + bottom_right[0]) / 2 - w / 2,
                bottom_right[1] + font_margin + base_height,
            ),
        ),
        (
            "bottom_right",
            lambda w: (
                bottom_right[0] - w - font_margin,
                bottom_right[1] + font_margin + base_height,
            ),
        ),
    ]

    for pos, get_position in positions:
        text = getattr(anim_reviewer.burn_in, pos)
        try:
            text = resolve_text(text, metadata)
        except Exception:
            logger.error(f'Error burn in text in {pos}: "{text}"')
            continue

        width, _ = blf.dimensions(font_id, text)
        pos_x, pos_y = get_position(width)
        blf.position(font_id, pos_x, pos_y, 0)
        blf.draw(font_id, text)


preview_handler = None


def register_or_unregister_preview_handler(
    mode: Literal["register", "unregister", "auto"] = "auto",
):
    """Register or unregister the preview burn-in handler.

    Preview handler only be registered when user enables the burn-in and preview.

    When this function is called by update of the burn-in properties,
    we can not access anim_reviewer.burn_in.enable directly, so we provide
    a mode parameter to force register or unregister.
    """
    global preview_handler

    if mode == "register":
        register = True
    elif mode == "unregister":
        register = False
    else:  # auto
        anim_reviewer = bpy.context.scene.anim_reviewer
        register = anim_reviewer.burn_in.enable and anim_reviewer.burn_in.preview

    if register is True and preview_handler is None:
        print("Register preview burn-in handler")
        preview_handler = bpy.types.SpaceView3D.draw_handler_add(
            preview_burn_in_handler, (), "WINDOW", "POST_PIXEL"
        )

    if register is False and preview_handler is not None:
        print("Unregister preview burn-in handler")
        bpy.types.SpaceView3D.draw_handler_remove(preview_handler, "WINDOW")
        preview_handler = None


@bpy.app.handlers.persistent
def load_post_handler(*args):
    register_or_unregister_preview_handler("auto")


def register():
    bpy.app.handlers.load_post.append(load_post_handler)

    # Delay the preview handler registration to avoid issues during startup
    bpy.app.timers.register(
        partial(register_or_unregister_preview_handler, "auto"),
        first_interval=0.1,
    )


def unregister():
    bpy.app.handlers.load_post.remove(load_post_handler)

    # Always unregister the preview handler on unload
    register_or_unregister_preview_handler("unregister")
