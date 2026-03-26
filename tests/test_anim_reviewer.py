import bpy
import pytest

BLENDER_VERSION = bpy.app.version


@pytest.fixture(autouse=True)
def new_scene():
    bpy.ops.scene.new(type="NEW")


@pytest.fixture()
def create_camera_and_cube():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()

    bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0))
    cube = bpy.context.active_object

    bpy.ops.object.camera_add(location=(0, -5, 0), rotation=(1.5708, 0, 0))
    camera = bpy.context.active_object

    constraint = camera.constraints.new(type="TRACK_TO")
    constraint.target = cube
    constraint.track_axis = "TRACK_NEGATIVE_Z"
    constraint.up_axis = "UP_Y"


@pytest.mark.skipif(BLENDER_VERSION >= (5, 0, 0), reason="Test for Blender 4.x")
def test_playblast_with_different_system_output_file_format(create_camera_and_cube):
    scene = bpy.context.scene

    anim_reviewer = bpy.context.scene.anim_reviewer
    anim_reviewer.override.use_frame_range = True
    anim_reviewer.override.frame_start = 1
    anim_reviewer.override.frame_end = 2

    scene.render.image_settings.file_format = "PNG"
    bpy.ops.render.anim_review(launch_player=False)

    scene.render.image_settings.file_format = "FFMPEG"
    bpy.ops.render.anim_review(launch_player=False)

    scene.render.image_settings.file_format = "OPEN_EXR_MULTILAYER1"
    bpy.ops.render.anim_review(launch_player=False)


if __name__ == "__main__":
    pytest.main([__file__])
