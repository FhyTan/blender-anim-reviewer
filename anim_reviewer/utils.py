import logging
import os
import platform
import shutil
import subprocess
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

import bpy
from bpy.app.translations import pgettext_rpt as rpt_

logger = logging.getLogger(__name__)


def get_full_font_name(ttf_path) -> str:
    from fontTools import ttLib

    with ttLib.TTFont(ttf_path) as font:
        full_name = font["name"].getDebugName(4)
    return full_name


def wait_for_file_stable(
    path: Path,
    timeout: float = 60.0,
    stable_samples: int = 2,
    interval: float = 0.3,
    grace: float = 0.5,
) -> bool:
    """Wait until `path` exists and its size stops growing.

    Since Blender 5.0, ``bpy.ops.sound.mixdown`` runs asynchronously in a
    background WM job, so the operator returns before the audio file is fully
    written. Polling until the file size stays stable ensures the file is
    complete and no longer locked before it is consumed or deleted.
    """

    deadline = time.monotonic() + timeout
    last_size = -1
    stable = 0

    while time.monotonic() < deadline:
        size = path.stat().st_size if path.exists() else -1

        if size > 0 and size == last_size:
            stable += 1
            if stable >= stable_samples:
                time.sleep(grace)
                return True
        else:
            last_size = size
            stable = 0

        time.sleep(interval)

    return False


@contextmanager
def temporary_directory(prefix: str = "blender_anim_reviewer_"):
    """Create a temporary directory that tolerates files locked on Windows.

    Blender's background mixdown job (or antivirus/OS indexers) may briefly
    keep files in the directory open, which makes ``TemporaryDirectory``
    cleanup raise PermissionError. Removal is retried and, as a last resort,
    the directory is left in the system temp folder instead of crashing.
    """

    dir_path = Path(tempfile.mkdtemp(prefix=prefix))
    try:
        yield dir_path
    finally:
        for _ in range(3):
            try:
                shutil.rmtree(dir_path)
                break
            except OSError:
                time.sleep(0.2)
        else:
            logger.warning(f"Can not remove temp dir {dir_path}, skipped!")


def detect_ffmpeg() -> bool:
    if shutil.which("ffmpeg"):
        return True

    # Fallback: try running "ffmpeg -version" to check if it's available in the system PATH.
    try:
        subprocess.check_output(["ffmpeg", "-version"], stderr=subprocess.STDOUT)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


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
    # new variable `found_version` added from blender 5.2.0
    found_version = (0, 0, 0)
    if preset == "CUSTOM":
        player_path = prefs.filepaths.animation_player
    else:
        if bpy.app.version >= (5, 2, 0):
            player_path, found_version = guess_player_path(preset)
        else:
            player_path = guess_player_path(preset)

    file = bpy.path.abspath(video_path)
    if not os.path.exists(file):
        err_msg = rpt_("File not found: {!r}").format(file)
        raise FileNotFoundError(err_msg)

    remove_OCIO_env = False
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
        if found_version >= (3, 4, 0):
            opts = [
                file,
                "-speed",
                str(fps_final),
                "-in",
                str(frame_start),
                "-out",
                str(frame_end),
                "-seek",
                str(scene.frame_current),
                "-timeUnits",
                "Frames",
            ]
        elif found_version >= (3, 0, 0):
            opts = [
                file,
                "-speed",
                str(fps_final),
            ]
        else:
            remove_OCIO_env = True
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
        env_copy = os.environ.copy()
        if remove_OCIO_env:
            env_copy.pop("OCIO", None)

        if platform.system() == "Windows":
            # CREATE_NEW_CONSOLE option can make the player display on top of the Blender window.
            subprocess.Popen(
                cmd,
                shell=True,
                env=env_copy,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
        else:
            # On non-Windows platforms, just launch the player without creating a new console.
            subprocess.Popen(cmd, env=env_copy)
    except Exception as ex:
        err_msg = rpt_(
            "Couldn't run external animation player with command {!r}\n{:s}"
        ).format(cmd, str(ex))
        raise RuntimeError(err_msg) from ex
