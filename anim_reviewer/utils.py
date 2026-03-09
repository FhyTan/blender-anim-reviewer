import os
import shutil
import subprocess

import bpy
from bpy.app.translations import pgettext_rpt as rpt_


def get_full_font_name(ttf_path) -> str:
    from fontTools import ttLib

    with ttLib.TTFont(ttf_path) as font:
        full_name = font["name"].getDebugName(4)
    return full_name


def detect_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def play_video(video_path: str):
    """Play a video file using the user's preferred application.

    This function adapts Blender's built-in `PlayRenderedAnim` operator.
    The original operator can only play files from the scene's render output path,
    which typically have names including frame ranges (e.g., "0001-0050.mkv").
    This implementation reuses and modifies the original source code to allow
    playing arbitrary video files.

    This function will only handle video playback, ignore image sequences.

    Original source code:
    https://projects.blender.org/blender/blender/src/branch/main/scripts/startup/bl_operators/screen_play_rendered_anim.py
    """

    from shlex import quote

    from bl_operators.screen_play_rendered_anim import guess_player_path

    context = bpy.context
    scene = context.scene
    rd = scene.render
    prefs = context.preferences
    fps_final = rd.fps / rd.fps_base

    preset = prefs.filepaths.animation_player_preset

    # try and guess a command line if it doesn't exist
    if preset == "CUSTOM":
        player_path = prefs.filepaths.animation_player
    else:
        player_path = guess_player_path(preset)

    file = bpy.path.abspath(video_path)
    if not os.path.exists(file):
        err_msg = rpt_("File not found: {!r}").format(file)
        raise FileNotFoundError(err_msg)

    cmd = [player_path]
    # extra options, fps controls etc.
    if scene.use_preview_range:
        frame_start = scene.frame_preview_start
        frame_end = scene.frame_preview_end
    else:
        frame_start = scene.frame_start
        frame_end = scene.frame_end
    if preset == "INTERNAL":
        # Use the current GPU backend for the player.
        import gpu

        gpu_backend = gpu.platform.backend_type_get()
        if gpu_backend not in {"NONE", "UNKNOWN"}:
            cmd.extend(
                [
                    "--gpu-backend",
                    gpu_backend.lower(),
                ]
            )
        del gpu, gpu_backend

        opts = [
            "-a",
            "-f",
            str(rd.fps),
            str(rd.fps_base),
            "-s",
            str(frame_start),
            "-e",
            str(frame_end),
            "-j",
            str(scene.frame_step),
            "-c",
            str(prefs.system.memory_cache_limit),
            file,
        ]
        cmd.extend(opts)
    elif preset == "DJV":
        opts = [
            file,
            "-speed",
            str(fps_final),
            "-in_out",
            str(frame_start),
            str(frame_end),
            "-frame",
            str(scene.frame_current),
            "-time_units",
            "Frames",
        ]
        cmd.extend(opts)
    elif preset == "FRAMECYCLER":
        opts = [file, "{:d}-{:d}".format(scene.frame_start, scene.frame_end)]
        cmd.extend(opts)
    elif preset == "RV":
        opts = ["-fps", str(rd.fps), "-play"]
        if scene.use_preview_range:
            opts += [
                file.replace("#", "", file.count("#") - 1),
                "{:d}-{:d}".format(frame_start, frame_end),
            ]
        else:
            opts.append(file)

        cmd.extend(opts)
    elif preset == "MPLAYER":
        opts = []
        opts.append(file)

        opts += ["-loop", "0", "-really-quiet", "-fs"]
        cmd.extend(opts)
    else:  # 'CUSTOM'
        cmd.append(file)

    # launch it
    print("Executing command:\n ", " ".join(quote(c) for c in cmd))

    try:
        subprocess.Popen(cmd)
    except Exception as ex:
        err_msg = rpt_(
            "Couldn't run external animation player with command {!r}\n{:s}"
        ).format(cmd, str(ex))
        raise RuntimeError(err_msg) from ex
