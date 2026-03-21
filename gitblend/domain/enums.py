"""Domain enumerations for gitblend."""

from enum import Enum, auto


class FileStatus(Enum):
    """Status of a file in the git working tree."""

    MODIFIED = auto()
    ADDED = auto()
    DELETED = auto()
    RENAMED = auto()
    COPIED = auto()
    UNTRACKED = auto()
    IGNORED = auto()
    CONFLICTED = auto()
    STAGED_MODIFIED = auto()
    STAGED_ADDED = auto()
    STAGED_DELETED = auto()
    STAGED_RENAMED = auto()


class ErrorKind(Enum):
    """Classifies the kind of error for UX routing."""

    USER = auto()        # user made a mistake (wrong input, wrong state)
    CONFIG = auto()      # misconfiguration (missing git binary, bad preferences)
    AUTH = auto()        # authentication failure (bad token, expired)
    REPO = auto()        # git repo state issue (not a repo, conflict, detached HEAD)
    NETWORK = auto()     # network / GitHub API failure
    CORRUPTION = auto()  # data integrity risk
    INTERNAL = auto()    # unexpected bug in gitblend itself


class BranchType(Enum):
    """Type of a git branch."""

    LOCAL = auto()
    REMOTE = auto()
    DETACHED = auto()


class SyncState(Enum):
    """Synchronization state with the upstream remote."""

    SYNCED = auto()
    AHEAD = auto()
    BEHIND = auto()
    DIVERGED = auto()
    NO_REMOTE = auto()
    UNKNOWN = auto()
