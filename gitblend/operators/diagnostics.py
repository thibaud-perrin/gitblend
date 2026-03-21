"""Operators: project audit, write gitignore/gitattributes, LFS setup."""

from __future__ import annotations

import bpy

from ..bpy_adapters import context as ctx_adapter
from ..bpy_adapters import reports
from ..domain.errors import NotBlenderProjectError
from ..domain.result import is_ok

from ._services import get_blender_project, get_diagnostics, get_lfs


class GITBLEND_OT_audit_project(bpy.types.Operator):
    bl_idname = "gitblend.audit_project"
    bl_label = "Audit Project"
    bl_description = "Check the project for portability issues before committing"

    def execute(self, context: bpy.types.Context) -> set[str]:
        blend_path = ctx_adapter.get_blend_path()
        if blend_path is None:
            reports.report_error(self, NotBlenderProjectError())
            return {"CANCELLED"}

        diag = get_diagnostics()
        project = get_blender_project()
        repo = project.detect_project_root(blend_path)

        result = diag.audit_project(repo, blend_path)
        if not is_ok(result):
            reports.report_error(self, result.error)  # type: ignore[union-attr]
            return {"CANCELLED"}

        report = result.value  # type: ignore[union-attr]
        props = context.window_manager.gitblend  # type: ignore[attr-defined]
        props.diag_has_gitignore = report.has_gitignore
        props.diag_has_gitattributes = report.has_gitattributes
        props.diag_large_file_count = len(report.files_exceeding_github_limit)
        props.diag_warning_count = report.warning_count

        if report.is_clean:
            self.report({"INFO"}, "Project looks good — no portability issues found.")
        else:
            self.report(
                {"WARNING"},
                f"Audit complete: {report.warning_count} issue(s) found.",
            )
        return {"FINISHED"}


class GITBLEND_OT_write_gitignore(bpy.types.Operator):
    bl_idname = "gitblend.write_gitignore"
    bl_label = "Create .gitignore"
    bl_description = "Write a Blender-appropriate .gitignore to the project root"

    def execute(self, context: bpy.types.Context) -> set[str]:
        blend_path = ctx_adapter.get_blend_path()
        if blend_path is None:
            return {"CANCELLED"}

        diag = get_diagnostics()
        project = get_blender_project()
        repo = project.detect_project_root(blend_path)

        result = diag.write_gitignore(repo)
        if is_ok(result):
            self.report({"INFO"}, ".gitignore created.")
        else:
            reports.report_error(self, result.error)  # type: ignore[union-attr]
            return {"CANCELLED"}
        return {"FINISHED"}


class GITBLEND_OT_write_gitattributes(bpy.types.Operator):
    bl_idname = "gitblend.write_gitattributes"
    bl_label = "Create .gitattributes"
    bl_description = "Write a .gitattributes file with git-lfs tracking rules"

    def execute(self, context: bpy.types.Context) -> set[str]:
        blend_path = ctx_adapter.get_blend_path()
        if blend_path is None:
            return {"CANCELLED"}

        diag = get_diagnostics()
        project = get_blender_project()
        repo = project.detect_project_root(blend_path)

        result = diag.write_gitattributes(repo)
        if is_ok(result):
            self.report({"INFO"}, ".gitattributes created. Commit this file.")
        else:
            reports.report_error(self, result.error)  # type: ignore[union-attr]
            return {"CANCELLED"}
        return {"FINISHED"}


class GITBLEND_OT_setup_lfs_blender(bpy.types.Operator):
    bl_idname = "gitblend.setup_lfs_blender"
    bl_label = "Setup LFS for Blender"
    bl_description = "Install git-lfs and configure it for all Blender binary types"

    def execute(self, context: bpy.types.Context) -> set[str]:
        if "CANCELLED" in bpy.ops.gitblend.setup_lfs():
            return {"CANCELLED"}
        bpy.ops.gitblend.write_gitattributes()
        return {"FINISHED"}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set[str]:
        if not get_lfs().is_lfs_available():
            self.report({"ERROR"}, "git-lfs is not installed. Install it from https://git-lfs.com/")
            return {"CANCELLED"}
        return context.window_manager.invoke_confirm(
            self,
            event,
            message="Setup git-lfs and write .gitattributes? This will modify the repo.",
        )


classes = [
    GITBLEND_OT_audit_project,
    GITBLEND_OT_write_gitignore,
    GITBLEND_OT_write_gitattributes,
    GITBLEND_OT_setup_lfs_blender,
]
