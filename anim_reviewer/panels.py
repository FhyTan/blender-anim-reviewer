import bpy
from bl_ui.utils import PresetPanel

from .metadata import META_DATA_DESCRIPTIONS


class ANIM_REVIEWER_PT_presets(PresetPanel, bpy.types.Panel):
    bl_label = "Anim Reviewer Presets"
    preset_subdir = "anim_reviewer"
    preset_operator = "script.execute_preset"
    preset_add_operator = "anim_reviewer.preset_add"

    @staticmethod
    def post_cb(context, _filepath):
        # Modify an arbitrary built-in scene property to force a depsgraph
        # update, because add-on properties don't. (see #62325)
        # This is derived from addons_core/cycles/ui.py
        scene = context.scene
        scene.frame_step = scene.frame_step


class ANIM_REVIEWER_PT_main(bpy.types.Panel):
    bl_idname = "ANIM_REVIEWER_PT_main"
    bl_label = "Anim Reviewer"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Tool"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header_preset(self, context):
        ANIM_REVIEWER_PT_presets.draw_panel_header(self.layout)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        video_props = context.scene.anim_reviewer.video
        layout.operator(
            "render.anim_review", text="Run Anim Review", icon="RENDER_ANIMATION"
        )
        layout.separator()

        col = layout.column()
        col.prop(video_props, "include_audio")
        col.prop(video_props, "codec")


class ANIM_REVIEWER_PT_override(bpy.types.Panel):
    bl_idname = "ANIM_REVIEWER_PT_override"
    bl_label = "Override"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Tool"
    bl_parent_id = "ANIM_REVIEWER_PT_main"
    bl_order = 0

    def draw(self, context: bpy.types.Context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        override_props = context.scene.anim_reviewer.override

        col = layout.column()

        col.prop(override_props, "scale")

        row = col.row(align=True, heading="Frame Range")
        row.prop(override_props, "use_frame_range", text="")
        sub = row.column()
        sub.active = override_props.use_frame_range
        sub.prop(override_props, "frame_start", text="Start")
        sub.prop(override_props, "frame_end", text="End")

        col.prop(override_props, "show_overlays", icon="OVERLAY")

        col = layout.column()
        row = col.row(align=True, heading="Viewport Shading")
        row.prop(override_props, "use_viewport_shading", text="")
        sub = row.row()
        sub.active = override_props.use_viewport_shading
        sub.prop(override_props, "viewport_shading", text="", expand=True)


class ANIM_REVIEWER_PT_file(bpy.types.Panel):
    bl_idname = "ANIM_REVIEWER_PT_file"
    bl_label = "File"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Tool"
    bl_parent_id = "ANIM_REVIEWER_PT_main"
    bl_order = 1

    def draw(self, context: bpy.types.Context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        file_props = context.scene.anim_reviewer.file

        col = layout.column()

        col.prop(
            file_props,
            "directory",
            placeholder="Default to current blend file directory",
        )
        col.prop(file_props, "name")

        row = col.row(align=True, heading="Version")
        row.prop(file_props, "use_version", text="")
        sub = row.row(align=True)
        sub.active = file_props.use_version
        sub.prop(file_props, "version", text="")

        col.prop(file_props, "extension")
        col.prop(file_props, "full_path")


class ANIM_REVIEWER_PT_burn_in(bpy.types.Panel):
    bl_idname = "ANIM_REVIEWER_PT_burn_in"
    bl_label = "Burn-In Data"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Tool"
    bl_parent_id = "ANIM_REVIEWER_PT_main"
    bl_order = 2

    def draw_header(self, context: bpy.types.Context):
        layout = self.layout

        burn_in_props = context.scene.anim_reviewer.burn_in
        layout.prop(burn_in_props, "enable", text="")
        layout.popover(panel="ANIM_REVIEWER_PT_burn_in_help", text="", icon="QUESTION")

    def draw(self, context: bpy.types.Context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        burn_in_props = context.scene.anim_reviewer.burn_in

        col = layout.column()
        col.enabled = burn_in_props.enable

        col = layout.column()
        col.enabled = burn_in_props.enable

        col.prop(burn_in_props, "preview")
        col.prop(burn_in_props, "font_family", placeholder="Default to Blender Font")
        col.prop(burn_in_props, "font_size")
        col.prop(burn_in_props, "margin")
        col.prop(burn_in_props, "color")
        col.prop(burn_in_props, "top_left")
        col.prop(burn_in_props, "top_center")
        col.prop(burn_in_props, "top_right")
        col.prop(burn_in_props, "bottom_left")
        col.prop(burn_in_props, "bottom_center")
        col.prop(burn_in_props, "bottom_right")


class ANIM_REVIEWER_PT_burn_in_help(bpy.types.Panel):
    bl_idname = "ANIM_REVIEWER_PT_burn_in_help"
    bl_label = "Burn-In Data Help"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Tool"
    bl_ui_units_x = 30
    bl_options = {"INSTANCED"}

    def draw(self, context: bpy.types.Context):
        layout = self.layout

        layout.label(
            text="Use curly braces {} to denote variables in text, for example {datetime} for the current time."
        )
        layout.label(text="The following variables are currently available:")
        grid = layout.grid_flow(row_major=True, columns=2)
        for key, description in META_DATA_DESCRIPTIONS.items():
            grid.label(text=f"{{{key}}}")
            grid.label(text=description)

        layout.separator()
        layout.label(
            text='You can also use the text like "{bpy.data.objects["Cube"].location[0]}" to access any Blender RNA data.'
        )
        layout.label(
            text='Tip: right-click any property, choose "Copy Full Data Path", then paste inside curly braces.'
        )


class ANIM_REVIEWER_PT_settings(bpy.types.Panel):
    bl_idname = "ANIM_REVIEWER_PT_settings"
    bl_label = "Settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Tool"
    bl_parent_id = "ANIM_REVIEWER_PT_main"
    bl_order = 3

    def draw(self, context: bpy.types.Context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False

        row = layout.row()
        row.operator("anim_reviewer.import_settings", text="Import", icon="IMPORT")
        row.operator("anim_reviewer.export_settings", text="Export", icon="EXPORT")


classes = (
    ANIM_REVIEWER_PT_presets,
    ANIM_REVIEWER_PT_main,
    ANIM_REVIEWER_PT_override,
    ANIM_REVIEWER_PT_file,
    ANIM_REVIEWER_PT_burn_in,
    ANIM_REVIEWER_PT_burn_in_help,
    ANIM_REVIEWER_PT_settings,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
