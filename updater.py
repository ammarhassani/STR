"""Self-update (#19): push once, every client updates itself — no per-PC visits.

Client PCs reach ONLY the shared folder (no repo/internet access), so the host
is the update hub:

  HOST   : git pull (host has repo access) -> publish a clean code snapshot to
           <share>/app/<version>/ and write <share>/app/latest.txt.
  CLIENT : on launch, compare local version to <share>/app/latest.txt; if newer,
           copy the snapshot over the app folder and record the new version.
  LOCAL  : single-PC install -> just git pull.

The launchers (deploy/start_host.vbs, deploy/start_client.vbs) run this before
the app. It is best-effort and NEVER fatal: on any error it logs and lets the
app start on the code already present. Migrations run at app startup, so a
pulled/copied schema change applies itself.

Rollback: the host keeps the last few version folders on the share; to roll a
client back, set its .str_version to an older version and it re-copies that one
(documented in HOST_RUNBOOK.md).
"""
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Optional, Tuple

_KEEP_VERSIONS = 5           # how many published snapshots to retain on the share
_VERSION_FILE = ".str_version"


# ----------------------------------------------------------------- git helpers
def _git(args, cwd) -> subprocess.CompletedProcess:
    return subprocess.run(["git"] + args, cwd=str(cwd),
                          capture_output=True, text=True, timeout=60)


def is_git_repo(repo_dir) -> bool:
    try:
        r = _git(["rev-parse", "--is-inside-work-tree"], repo_dir)
        return r.returncode == 0 and r.stdout.strip() == "true"
    except (FileNotFoundError, subprocess.SubprocessError):
        return False


def has_local_changes(repo_dir) -> bool:
    r = _git(["status", "--porcelain"], repo_dir)
    return bool(r.stdout.strip())


def current_version(repo_dir) -> Optional[str]:
    """Short commit id of the repo HEAD (the published version tag)."""
    try:
        r = _git(["rev-parse", "--short", "HEAD"], repo_dir)
        return r.stdout.strip() if r.returncode == 0 else None
    except (FileNotFoundError, subprocess.SubprocessError):
        return None


def self_update_via_git(repo_dir) -> Tuple[bool, str]:
    """Fast-forward pull if safe (host / single-PC). Never raises."""
    try:
        if not is_git_repo(repo_dir):
            return False, "Not a git checkout — skipping git update."
        if has_local_changes(repo_dir):
            return False, "Local changes present — git update skipped (resolve manually)."
        r = _git(["pull", "--ff-only"], repo_dir)
        out = (r.stdout + "\n" + r.stderr).strip()
        if r.returncode != 0:
            last = out.splitlines()[-1] if out else "unknown error"
            return False, f"git update failed (offline?): {last}"
        if "Already up to date" in out or "up-to-date" in out:
            return False, "Already up to date."
        return True, "Pulled latest code."
    except FileNotFoundError:
        return False, "git not installed — skipping git update."
    except subprocess.TimeoutExpired:
        return False, "git update timed out (offline?)."
    except Exception as e:
        return False, f"git update skipped: {e}"


# --------------------------------------------------------------- host: publish
def publish_to_share(repo_dir, share_dir) -> Tuple[bool, str]:
    """Export a clean snapshot of the tracked code to <share>/app/<version>/ and
    point latest.txt at it. Only tracked files are published (no db, logs, config,
    .git). Returns (published, message)."""
    try:
        if not is_git_repo(repo_dir):
            return False, "Host is not a git checkout — cannot publish."
        version = current_version(repo_dir)
        if not version:
            return False, "Could not determine version — publish skipped."
        app_root = Path(share_dir) / "app"
        dest = app_root / version
        latest = app_root / "latest.txt"

        if dest.exists() and latest.exists() and latest.read_text(encoding="utf-8").strip() == version:
            return False, f"Share already has version {version}."

        app_root.mkdir(parents=True, exist_ok=True)
        # git archive -> a tar of exactly the tracked files at HEAD, then extract.
        with tempfile.TemporaryDirectory() as tmp:
            tar_path = Path(tmp) / "snapshot.tar"
            r = _git(["archive", "--format=tar", "-o", str(tar_path), "HEAD"], repo_dir)
            if r.returncode != 0:
                return False, f"git archive failed: {r.stderr.strip()}"
            staging = dest.with_name(f".{version}.staging")
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)
            staging.mkdir(parents=True)
            with tarfile.open(tar_path) as tf:
                tf.extractall(staging)
            # atomic-ish swap: remove any partial dest, then rename staging in
            if dest.exists():
                shutil.rmtree(dest, ignore_errors=True)
            staging.rename(dest)

        # publish latest.txt LAST so a client never sees a version before its files
        latest.write_text(version + "\n", encoding="utf-8")
        _prune_old_versions(app_root, keep=_KEEP_VERSIONS, current=version)
        return True, f"Published version {version} to the share."
    except Exception as e:
        return False, f"Publish skipped: {e}"


def _prune_old_versions(app_root: Path, keep: int, current: str):
    """Keep the newest `keep` version folders (by mtime); always keep current."""
    try:
        dirs = [d for d in app_root.iterdir() if d.is_dir() and not d.name.startswith(".")]
        dirs.sort(key=lambda d: d.stat().st_mtime, reverse=True)
        for d in dirs[keep:]:
            if d.name != current:
                shutil.rmtree(d, ignore_errors=True)
    except Exception:
        pass


# ------------------------------------------------------------- client: consume
def _read_local_version(app_dir) -> Optional[str]:
    f = Path(app_dir) / _VERSION_FILE
    return f.read_text(encoding="utf-8").strip() if f.exists() else None


def update_from_share(app_dir, share_dir) -> Tuple[bool, str]:
    """Copy the latest published snapshot from the share over the app folder if
    it is newer than what this PC runs. Never raises. Only overlays tracked code
    files — the local db/config/logs are untouched (they aren't in the snapshot)."""
    try:
        app_root = Path(share_dir) / "app"
        latest = app_root / "latest.txt"
        if not latest.exists():
            return False, "No published version on the share yet — using current code."
        want = latest.read_text(encoding="utf-8").strip()
        if not want:
            return False, "Empty latest.txt on the share — using current code."
        if _read_local_version(app_dir) == want:
            return False, f"Already on version {want}."
        snapshot = app_root / want
        if not snapshot.is_dir():
            return False, f"Published version {want} missing on the share — using current code."

        # overlay every file from the snapshot onto the app folder, but NEVER
        # touch per-machine state — config and the version file belong to this PC
        # (defense-in-depth; they are gitignored so shouldn't be in a snapshot).
        copied = 0
        for src in snapshot.rglob("*"):
            if src.is_dir():
                continue
            rel = src.relative_to(snapshot)
            rel_posix = rel.as_posix()
            if rel_posix == _VERSION_FILE or rel_posix.startswith("config/") or rel_posix.startswith("logs/"):
                continue
            target = Path(app_dir) / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)
            copied += 1
        (Path(app_dir) / _VERSION_FILE).write_text(want + "\n", encoding="utf-8")
        return True, f"Updated to version {want} from the share ({copied} files). Restart applies it."
    except Exception as e:
        return False, f"Share update skipped: {e}"


# ---------------------------------------------------------------------- driver
def run(app_dir=None) -> Tuple[bool, str]:
    """Dispatch by configured mode. Returns (changed, message)."""
    app_dir = Path(app_dir) if app_dir else Path(__file__).resolve().parent
    try:
        from config import Config
        Config.load()
        mode = getattr(Config, "MODE", "local")
        share = getattr(Config, "SHARE_PATH", None)
    except Exception:
        mode, share = "local", None

    if mode == "host":
        pulled, pmsg = self_update_via_git(app_dir)
        pub_changed, pubmsg = (publish_to_share(app_dir, share) if share
                               else (False, "No share configured — publish skipped."))
        return (pulled or pub_changed), f"{pmsg} {pubmsg}"
    if mode == "client":
        if not share:
            return False, "No share configured — cannot self-update."
        return update_from_share(app_dir, share)
    # local single-PC install
    return self_update_via_git(app_dir)


def main() -> int:
    changed, msg = run()
    print(f"[updater] {msg}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
