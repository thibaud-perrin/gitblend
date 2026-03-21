"""Operators: GitHub auth, remote repo, pull requests, releases."""

from __future__ import annotations

import webbrowser

import bpy

from ..bpy_adapters import context as ctx_adapter
from ..bpy_adapters import jobs, reports
from ..domain.errors import NotBlenderProjectError
from ..domain.result import is_ok

from ._services import get_auth, get_blender_project, get_git, get_github

_device_flow_pending: bool = False


class GITBLEND_OT_auth_pat(bpy.types.Operator):
    bl_idname = "gitblend.auth_pat"
    bl_label = "Connect with Token"
    bl_description = "Authenticate with GitHub using a Personal Access Token"

    token: bpy.props.StringProperty(  # type: ignore[valid-type]
        name="GitHub Token",
        subtype="PASSWORD",
        default="",
    )

    def execute(self, context: bpy.types.Context) -> set[str]:
        token = self.token.strip()
        if not token:
            self.report({"WARNING"}, "Token cannot be empty.")
            return {"CANCELLED"}

        github = get_github()
        result = github.authenticate_pat(token)
        if is_ok(result):
            username = result.value  # type: ignore[union-attr]
            self.report({"INFO"}, f"Connected to GitHub as {username}.")
            props = context.window_manager.gitblend  # type: ignore[attr-defined]
            props.github_username = username
            props.github_authenticated = True
        else:
            reports.report_error(self, result.error)  # type: ignore[union-attr]
            return {"CANCELLED"}
        return {"FINISHED"}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set[str]:
        return context.window_manager.invoke_props_dialog(self, width=400)

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        layout.label(text="Enter your GitHub Personal Access Token:")
        layout.prop(self, "token", text="")
        layout.separator()
        layout.operator(
            "wm.url_open",
            text="Generate token on GitHub",
            icon="URL",
        ).url = "https://github.com/settings/tokens/new"


class GITBLEND_OT_start_device_flow(bpy.types.Operator):
    bl_idname = "gitblend.start_device_flow"
    bl_label = "Connect via Browser"
    bl_description = "Authenticate with GitHub using the device authorization flow"

    def execute(self, context: bpy.types.Context) -> set[str]:
        global _device_flow_pending
        if _device_flow_pending:
            self.report({"WARNING"}, "GitHub connection already in progress...")
            return {"CANCELLED"}

        _device_flow_pending = True
        github = get_github()

        def do_start():
            return github.start_device_flow()

        def on_complete(result):
            global _device_flow_pending
            _device_flow_pending = False
            if not is_ok(result):
                error = result.error  # type: ignore[union-attr]
                msg = error.message
                if error.detail:
                    msg = f"{msg}: {error.detail}"
                reports.popup_message(msg, title="GitHub Connection Failed", icon="ERROR")
                return
            flow = result.value  # type: ignore[union-attr]
            try:
                props = bpy.context.window_manager.gitblend  # type: ignore[attr-defined]
                props.device_flow_code = flow.user_code
                props.device_flow_uri = flow.verification_uri
                props.device_flow_device_code = flow.device_code
            except Exception:
                pass
            webbrowser.open(flow.verification_uri)
            bpy.ops.gitblend.show_device_flow_popup("INVOKE_DEFAULT")

        def on_error(exc: Exception) -> None:
            global _device_flow_pending
            _device_flow_pending = False
            reports.popup_message(str(exc), title="GitHub Connection Failed", icon="ERROR")

        jobs.run_in_background(do_start, on_complete, on_error)
        self.report({"INFO"}, "Connecting to GitHub...")
        return {"FINISHED"}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set[str]:
        return self.execute(context)


class GITBLEND_OT_show_device_flow_popup(bpy.types.Operator):
    bl_idname = "gitblend.show_device_flow_popup"
    bl_label = "GitHub Device Authorization"

    def execute(self, context: bpy.types.Context) -> set[str]:
        return {"FINISHED"}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set[str]:
        return context.window_manager.invoke_popup(self, width=400)

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        layout.label(text="Open the link below and enter this code:", icon="URL")
        layout.separator()
        row = layout.row()
        row.scale_y = 2.0
        props = context.window_manager.gitblend  # type: ignore[attr-defined]
        row.label(text=props.device_flow_code, icon="KEYINGSET")
        layout.separator()
        layout.label(text=props.device_flow_uri)
        layout.separator()
        layout.operator("gitblend.poll_device_flow", text="I've authorized — continue", icon="CHECKMARK")


class GITBLEND_OT_poll_device_flow(bpy.types.Operator):
    bl_idname = "gitblend.poll_device_flow"
    bl_label = "Complete Device Flow"
    bl_description = "Check if GitHub device authorization is complete"

    def execute(self, context: bpy.types.Context) -> set[str]:
        github = get_github()
        props = context.window_manager.gitblend  # type: ignore[attr-defined]

        # We stored device_code in props during start_device_flow
        device_code = getattr(props, "device_flow_device_code", "")
        if not device_code:
            self.report({"WARNING"}, "No active device flow. Start again.")
            return {"CANCELLED"}

        result = github.poll_device_flow(device_code, max_attempts=1)
        if is_ok(result):
            # Get username
            user_result = github.get_authenticated_user()
            username = user_result.value if is_ok(user_result) else ""  # type: ignore[union-attr]
            props.github_username = username
            props.github_authenticated = True
            if username:
                get_auth().save_meta("github.com", "username", username)
            self.report({"INFO"}, f"Connected to GitHub as {username}.")
        else:
            self.report({"WARNING"}, "Not authorized yet. Try again in a moment.")
            return {"CANCELLED"}

        return {"FINISHED"}


class GITBLEND_OT_github_logout(bpy.types.Operator):
    bl_idname = "gitblend.github_logout"
    bl_label = "Disconnect GitHub"
    bl_description = "Remove stored GitHub credentials"

    def execute(self, context: bpy.types.Context) -> set[str]:
        github = get_github()
        github.logout()
        props = context.window_manager.gitblend  # type: ignore[attr-defined]
        props.github_username = ""
        props.github_authenticated = False
        self.report({"INFO"}, "Disconnected from GitHub.")
        return {"FINISHED"}


class GITBLEND_OT_create_remote_repo(bpy.types.Operator):
    bl_idname = "gitblend.create_remote_repo"
    bl_label = "Create GitHub Repository"
    bl_description = "Create a new repository on GitHub and link it as origin"

    repo_name: bpy.props.StringProperty(name="Repository name", default="")  # type: ignore[valid-type]
    private: bpy.props.BoolProperty(name="Private", default=True)  # type: ignore[valid-type]
    description: bpy.props.StringProperty(name="Description", default="")  # type: ignore[valid-type]

    def execute(self, context: bpy.types.Context) -> set[str]:
        blend_path = ctx_adapter.get_blend_path()
        if blend_path is None:
            reports.report_error(self, NotBlenderProjectError())
            return {"CANCELLED"}

        name = self.repo_name.strip()
        if not name:
            self.report({"WARNING"}, "Repository name cannot be empty.")
            return {"CANCELLED"}

        github = get_github()
        result = github.create_repo(name, private=self.private, description=self.description)
        if not is_ok(result):
            reports.report_error(self, result.error)  # type: ignore[union-attr]
            return {"CANCELLED"}

        repo_info = result.value  # type: ignore[union-attr]

        # Add as remote
        git = get_git()
        project = get_blender_project()
        local_repo = project.detect_project_root(blend_path)

        add_result = git.add_remote(local_repo, "origin", repo_info.clone_url)
        if not is_ok(add_result):
            # Remote may already exist — update it
            git.set_remote_url(local_repo, "origin", repo_info.clone_url)

        self.report({"INFO"}, f"Repository '{repo_info.full_name}' created and linked.")
        props = context.window_manager.gitblend  # type: ignore[attr-defined]
        props.remote_repo_url = repo_info.url
        return {"FINISHED"}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set[str]:
        blend_path = ctx_adapter.get_blend_path()
        if blend_path and not self.repo_name:
            self.repo_name = blend_path.stem
        return context.window_manager.invoke_props_dialog(self, width=350)

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        layout.prop(self, "repo_name")
        layout.prop(self, "description")
        layout.prop(self, "private")


class GITBLEND_OT_create_pr(bpy.types.Operator):
    bl_idname = "gitblend.create_pr"
    bl_label = "Create Pull Request"
    bl_description = "Create a Pull Request on GitHub"

    pr_title: bpy.props.StringProperty(name="Title", default="")  # type: ignore[valid-type]
    pr_body: bpy.props.StringProperty(name="Description", default="")  # type: ignore[valid-type]
    base_branch: bpy.props.StringProperty(name="Base branch", default="main")  # type: ignore[valid-type]

    def execute(self, context: bpy.types.Context) -> set[str]:
        blend_path = ctx_adapter.get_blend_path()
        if blend_path is None:
            return {"CANCELLED"}

        git = get_git()
        github = get_github()
        project = get_blender_project()
        repo = project.detect_project_root(blend_path)

        # Get current branch as head
        status_result = git.status(repo)
        if not is_ok(status_result):
            return {"CANCELLED"}
        head_branch = status_result.value.branch  # type: ignore[union-attr]

        # Get owner/name from remote
        remotes_result = git.list_remotes(repo)
        if not is_ok(remotes_result) or not remotes_result.value:  # type: ignore[union-attr]
            self.report({"WARNING"}, "No remote configured.")
            return {"CANCELLED"}
        remote_url = remotes_result.value[0].url  # type: ignore[union-attr]
        owner, repo_name = _parse_github_owner_repo(remote_url)

        result = github.create_pr(
            owner, repo_name,
            title=self.pr_title or f"Update {head_branch}",
            head=head_branch,
            base=self.base_branch,
            body=self.pr_body,
        )
        if is_ok(result):
            pr = result.value  # type: ignore[union-attr]
            self.report({"INFO"}, f"PR #{pr.number} created.")
            webbrowser.open(pr.url)
        else:
            reports.report_error(self, result.error)  # type: ignore[union-attr]
            return {"CANCELLED"}
        return {"FINISHED"}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set[str]:
        return context.window_manager.invoke_props_dialog(self, width=400)

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        layout.prop(self, "pr_title")
        layout.prop(self, "base_branch")
        layout.prop(self, "pr_body")


class GITBLEND_OT_open_github(bpy.types.Operator):
    bl_idname = "gitblend.open_github"
    bl_label = "Open on GitHub"
    bl_description = "Open the GitHub repository in the browser"

    def execute(self, context: bpy.types.Context) -> set[str]:
        blend_path = ctx_adapter.get_blend_path()
        if blend_path is None:
            return {"CANCELLED"}

        git = get_git()
        project = get_blender_project()
        repo = project.detect_project_root(blend_path)

        remotes_result = git.list_remotes(repo)
        if not is_ok(remotes_result) or not remotes_result.value:  # type: ignore[union-attr]
            self.report({"WARNING"}, "No remote configured.")
            return {"CANCELLED"}

        url = remotes_result.value[0].url  # type: ignore[union-attr]
        if url.startswith("git@github.com:"):
            url = url.replace("git@github.com:", "https://github.com/", 1)
        url = url.rstrip(".git")
        webbrowser.open(url)
        return {"FINISHED"}


class GITBLEND_OT_create_release(bpy.types.Operator):
    bl_idname = "gitblend.create_release"
    bl_label = "Create Release"
    bl_description = "Create a GitHub release from the current commit"

    tag_name: bpy.props.StringProperty(name="Tag", default="v0.1.0")  # type: ignore[valid-type]
    release_name: bpy.props.StringProperty(name="Name", default="")  # type: ignore[valid-type]
    body: bpy.props.StringProperty(name="Notes", default="")  # type: ignore[valid-type]
    prerelease: bpy.props.BoolProperty(name="Pre-release", default=False)  # type: ignore[valid-type]

    def execute(self, context: bpy.types.Context) -> set[str]:
        blend_path = ctx_adapter.get_blend_path()
        if blend_path is None:
            return {"CANCELLED"}

        git = get_git()
        github = get_github()
        project = get_blender_project()
        repo = project.detect_project_root(blend_path)

        # First create and push the tag
        tag_result = git.create_tag(repo, self.tag_name, message=self.release_name or self.tag_name)
        if not is_ok(tag_result):
            reports.report_error(self, tag_result.error)  # type: ignore[union-attr]
            return {"CANCELLED"}
        git.push_tags(repo)

        remotes_result = git.list_remotes(repo)
        if not is_ok(remotes_result) or not remotes_result.value:  # type: ignore[union-attr]
            self.report({"WARNING"}, "No remote configured.")
            return {"CANCELLED"}
        remote_url = remotes_result.value[0].url  # type: ignore[union-attr]
        owner, repo_name = _parse_github_owner_repo(remote_url)

        result = github.create_release(
            owner, repo_name,
            tag=self.tag_name,
            name=self.release_name or self.tag_name,
            body=self.body,
            prerelease=self.prerelease,
        )
        if is_ok(result):
            release = result.value  # type: ignore[union-attr]
            self.report({"INFO"}, f"Release {release.tag} created.")
            webbrowser.open(release.url)
        else:
            reports.report_error(self, result.error)  # type: ignore[union-attr]
            return {"CANCELLED"}
        return {"FINISHED"}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event) -> set[str]:
        return context.window_manager.invoke_props_dialog(self, width=350)

    def draw(self, context: bpy.types.Context) -> None:
        layout = self.layout
        layout.prop(self, "tag_name")
        layout.prop(self, "release_name")
        layout.prop(self, "body")
        layout.prop(self, "prerelease")


def _parse_github_owner_repo(url: str) -> tuple[str, str]:
    """Extract (owner, repo) from a GitHub remote URL."""
    url = url.rstrip("/").rstrip(".git")
    if url.startswith("git@github.com:"):
        path = url[len("git@github.com:"):]
    elif "github.com/" in url:
        path = url.split("github.com/", 1)[1]
    else:
        return "", ""
    parts = path.split("/")
    if len(parts) >= 2:
        return parts[0], parts[1]
    return "", ""


classes = [
    GITBLEND_OT_auth_pat,
    GITBLEND_OT_start_device_flow,
    GITBLEND_OT_show_device_flow_popup,
    GITBLEND_OT_poll_device_flow,
    GITBLEND_OT_github_logout,
    GITBLEND_OT_create_remote_repo,
    GITBLEND_OT_create_pr,
    GITBLEND_OT_open_github,
    GITBLEND_OT_create_release,
]
