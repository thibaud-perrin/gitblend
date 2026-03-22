"""gitblend — Git and GitHub workflows for Blender projects.

This is the Blender extension entry point. Registration is delegated
to registration.py to keep this file minimal.
"""

# The authoritative metadata is in blender_manifest.toml.
# bl_info is kept for backwards compatibility with Blender < 4.2.
bl_info = {
    "name": "gitblend",
    "author": "gitblend contributors",
    "version": (0, 2, 4),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Git",
    "description": "Git and GitHub workflows for Blender projects.",
    "category": "Development",
    "doc_url": "https://github.com/hallcyn/gitblend",
    "tracker_url": "https://github.com/hallcyn/gitblend/issues",
}


def register() -> None:
    from .registration import register as _register
    _register()


def unregister() -> None:
    from .registration import unregister as _unregister
    _unregister()
