"""Operators: setup Git LFS, check LFS status."""

from __future__ import annotations

import bpy

from ..bpy_adapters import context as ctx_adapter
from ..bpy_adapters import reports
from ..domain.errors import NotBlenderProjectError
from ..domain.result import is_ok

from ._services import get_blender_project, get_lfs


class GITBLEND_OT_setup_lfs(bpy.types.Operator):
    bl_idname = "gitblend.setup_lfs"
    bl_label = "Setup Git LFS"
    bl_description = "Install git-lfs and track standard Blender binary patterns"

    def execute(self, context: bpy.types.Context) -> set[str]:
        blend_path = ctx_adapter.get_blend_path()
        if blend_path is None:
            reports.report_error(self, NotBlenderProjectError())
            return {"CANCELLED"}

        lfs = get_lfs()
        if not lfs.is_lfs_available():
            self.report(
                {"ERROR"},
                "git-lfs is not installed. Install it from https://git-lfs.com/",
            )
            return {"CANCELLED"}

        project = get_blender_project()
        repo = project.detect_project_root(blend_path)

        result = lfs.setup_for_blender(repo)
        if is_ok(result):
            patterns = result.value  # type: ignore[union-attr]
            self.report({"INFO"}, f"LFS set up: {len(patterns)} patterns tracked. Commit .gitattributes.")
        else:
            reports.report_error(self, result.error)  # type: ignore[union-attr]
            return {"CANCELLED"}
        return {"FINISHED"}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set[str]:
        return context.window_manager.invoke_confirm(
            self,
            event,
            message="Set up git-lfs for all Blender binary types? This modifies .gitattributes.",
        )


class GITBLEND_OT_check_lfs(bpy.types.Operator):
    bl_idname = "gitblend.check_lfs"
    bl_label = "Check Large Files"
    bl_description = "Find large files that should be tracked by git-lfs"

    def execute(self, context: bpy.types.Context) -> set[str]:
        blend_path = ctx_adapter.get_blend_path()
        if blend_path is None:
            return {"CANCELLED"}

        lfs = get_lfs()
        project = get_blender_project()
        repo = project.detect_project_root(blend_path)

        result = lfs.check_files_need_lfs(repo)
        if is_ok(result):
            files = result.value  # type: ignore[union-attr]
            if files:
                names = ", ".join(str(f.path) for f in files[:5])
                self.report({"WARNING"}, f"{len(files)} large file(s) found: {names}")
            else:
                self.report({"INFO"}, "No large files detected outside LFS.")
        else:
            reports.report_error(self, result.error)  # type: ignore[union-attr]

        return {"FINISHED"}


classes = [
    GITBLEND_OT_setup_lfs,
    GITBLEND_OT_check_lfs,
]
