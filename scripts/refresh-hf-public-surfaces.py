#!/usr/bin/env python3
"""Refresh public SafeRide Hugging Face cards without touching artifact bytes."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import stat
import tempfile
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TOKEN_ENV = "SAFERIDE_HF_TOKEN"
EXPECTED_OWNER_IDENTITY = "esherialabs"
NOTICE_PATH = ROOT / "docs/qa/saferide-gemma-3n-superseded-notice-2026-08-18.md"
LEGACY_PUBLIC_LINK_REPLACEMENTS: tuple[tuple[bytes, bytes], ...] = (
    (
        b"https://github.com/esherialabs/saferider",
        b"https://github.com/esherialabs/saferide",
    ),
)

REPOSITORIES: tuple[dict[str, str], ...] = (
    {
        "key": "mobile",
        "repo_id": "esherialabs/saferide-gemma-4-e2b-v058-original-419806-litertlm",
        "repo_type": "model",
        "expected_head": "ce0b969d2ef747b43b91b7278cf1c297efc0f666",
        "local_readme": "docs/qa/saferide-gemma4-e2b-v058-litertlm-model-card-2026-08-10.md",
        "message": "Refresh Android testing and project links",
    },
    {
        "key": "adapter",
        "repo_id": "esherialabs/saferide-gemma-4-e2b-v058-original-419806-adapter",
        "repo_type": "model",
        "expected_head": "42d98ef60eddcc280e1e3c3a0b78ff44842c1d98",
        "local_readme": "docs/qa/saferide-gemma4-e2b-v058-adapter-model-card-2026-08-11.md",
        "message": "Add current SafeRide project links",
    },
    {
        "key": "dataset",
        "repo_id": "esherialabs/saferide-gemma-4-e2b-v058-original-419806-training-data",
        "repo_type": "dataset",
        "expected_head": "da760c09e0d51e929778d10db749b5bb60cfa70c",
        "local_readme": "docs/qa/saferide-gemma4-v058-dataset-card-2026-08-11.md",
        "message": "Add current SafeRide project links",
    },
    {
        "key": "legacy",
        "repo_id": "esherialabs/saferide-gemma-3n",
        "repo_type": "model",
        "expected_head": "a1f511656e759927bcab2af6ff87e129e2c4689f",
        "local_readme": "",
        "message": "Mark Gemma 3n model as superseded",
    },
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm-owner-authorized", action="store_true")
    parser.add_argument("--result", help="Private result path outside the repository")
    return parser.parse_args()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def import_hub() -> tuple[Any, Any]:
    try:
        from huggingface_hub import HfApi, hf_hub_download
    except ImportError as error:
        raise RuntimeError("Install huggingface_hub before refreshing public cards.") from error
    return HfApi, hf_hub_download


def repo_info(api: Any, spec: dict[str, str], token: Any, revision: str | None = None) -> Any:
    kwargs = {"token": token, "files_metadata": True}
    if revision is not None:
        kwargs["revision"] = revision
    if spec["repo_type"] == "dataset":
        return api.dataset_info(spec["repo_id"], **kwargs)
    return api.model_info(spec["repo_id"], **kwargs)


def non_readme_inventory(info: Any) -> list[tuple[str, int | None, str | None]]:
    result = []
    for item in info.siblings:
        if item.rfilename == "README.md":
            continue
        lfs_hash = None if item.lfs is None else item.lfs.sha256
        result.append((item.rfilename, item.size, lfs_hash))
    return sorted(result)


def place_notice_after_front_matter(historical: bytes, notice: bytes) -> bytes:
    normalized_notice = notice.rstrip() + b"\n\n"
    content = historical
    for old_link, current_link in LEGACY_PUBLIC_LINK_REPLACEMENTS:
        content = content.replace(old_link, current_link)
    if content.startswith(normalized_notice):
        content = content[len(normalized_notice):]

    if not content.startswith(b"---\n"):
        return normalized_notice + content

    closing_marker = b"\n---\n"
    closing_index = content.find(closing_marker, 4)
    require(closing_index >= 0, "Legacy model card has malformed YAML metadata.")
    body_index = closing_index + len(closing_marker)
    front_matter = content[:body_index]
    body = content[body_index:].lstrip(b"\n")
    if body.startswith(normalized_notice):
        body = body[len(normalized_notice):]
    return front_matter + b"\n" + normalized_notice + body


def local_readmes(hf_hub_download: Any) -> dict[str, bytes]:
    notice = NOTICE_PATH.read_bytes()
    values: dict[str, bytes] = {}
    for spec in REPOSITORIES:
        if spec["key"] != "legacy":
            local_path = ROOT / spec["local_readme"]
            require(local_path.is_file(), f"Missing local card: {local_path}")
            values[spec["key"]] = local_path.read_bytes()
            continue
        with tempfile.TemporaryDirectory(prefix="saferide-hf-legacy-") as temporary:
            downloaded = Path(
                hf_hub_download(
                    repo_id=spec["repo_id"],
                    filename="README.md",
                    repo_type=spec["repo_type"],
                    revision=spec["expected_head"],
                    token=False,
                    local_dir=temporary,
                )
            )
            historical = downloaded.read_bytes()
        values[spec["key"]] = place_notice_after_front_matter(historical, notice)
    return values


def write_private_result(path_text: str, value: dict[str, Any]) -> None:
    path = Path(path_text).expanduser().resolve()
    require(ROOT not in path.parents and path != ROOT, "Result must remain outside the repository.")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    path.chmod(0o600)
    require(stat.S_IMODE(path.stat().st_mode) & 0o077 == 0, "Result permissions are too broad.")


def main() -> None:
    args = parse_args()
    HfApi, hf_hub_download = import_hub()
    readmes = local_readmes(hf_hub_download)

    if not args.execute:
        for spec in REPOSITORIES:
            value = readmes[spec["key"]]
            print(f"{spec['repo_id']} README.md {len(value)} bytes sha256={sha256(value)}")
        return

    require(args.confirm_owner_authorized, "Owner authorization flag is required.")
    require(args.result, "--result is required with --execute.")
    token = os.environ.pop(TOKEN_ENV, "")
    require(bool(token), f"{TOKEN_ENV} is required.")

    api = HfApi(token=token)
    identity = api.whoami(token=token)
    require(
        identity.get("name") == EXPECTED_OWNER_IDENTITY,
        "Unexpected Hugging Face identity.",
    )

    result: dict[str, Any] = {
        "schemaVersion": 1,
        "recordedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "publishing",
        "artifactBytesChanged": False,
        "repositories": {},
    }
    write_private_result(args.result, result)

    for spec in REPOSITORIES:
        before = repo_info(api, spec, token)
        require(before.private is False, f"Repository is not public: {spec['repo_id']}")
        require(getattr(before, "gated", False) is False, f"Repository is gated: {spec['repo_id']}")
        require(before.sha == spec["expected_head"], f"Unexpected head for {spec['repo_id']}: {before.sha}")
        inventory = non_readme_inventory(before)

        with tempfile.TemporaryDirectory(prefix=f"saferide-hf-current-{spec['key']}-") as temporary:
            current_readme = Path(
                hf_hub_download(
                    repo_id=spec["repo_id"],
                    filename="README.md",
                    repo_type=spec["repo_type"],
                    revision=spec["expected_head"],
                    token=False,
                    local_dir=temporary,
                )
            ).read_bytes()
        readme_changed = current_readme != readmes[spec["key"]]

        if readme_changed:
            with tempfile.TemporaryDirectory(prefix=f"saferide-hf-{spec['key']}-") as temporary:
                local_readme = Path(temporary) / "README.md"
                local_readme.write_bytes(readmes[spec["key"]])
                commit = api.upload_file(
                    path_or_fileobj=str(local_readme),
                    path_in_repo="README.md",
                    repo_id=spec["repo_id"],
                    repo_type=spec["repo_type"],
                    revision="main",
                    commit_message=spec["message"],
                    parent_commit=spec["expected_head"],
                    token=token,
                )
            revision = commit.oid
            require(isinstance(revision, str) and len(revision) == 40, "Hugging Face returned no commit SHA.")
        else:
            revision = before.sha
        after = repo_info(api, spec, token, revision=revision)
        require(non_readme_inventory(after) == inventory, f"Artifact inventory changed: {spec['repo_id']}")

        verified = False
        for attempt in range(6):
            try:
                with tempfile.TemporaryDirectory(prefix=f"saferide-hf-verify-{spec['key']}-") as temporary:
                    downloaded = Path(
                        hf_hub_download(
                            repo_id=spec["repo_id"],
                            filename="README.md",
                            repo_type=spec["repo_type"],
                            revision=revision,
                            token=False,
                            local_dir=temporary,
                            force_download=True,
                        )
                    )
                    verified = downloaded.read_bytes() == readmes[spec["key"]]
                if verified:
                    break
            except Exception:
                pass
            if attempt < 5:
                time.sleep(2)
        require(verified, f"Anonymous README verification failed: {spec['repo_id']}")
        result["repositories"][spec["key"]] = {
            "repoId": spec["repo_id"],
            "priorHead": spec["expected_head"],
            "newHead": revision,
            "readmeSha256": sha256(readmes[spec["key"]]),
            "anonymousReadbackVerified": True,
            "artifactInventoryUnchanged": True,
            "readmeChanged": readme_changed,
        }
        write_private_result(args.result, result)

    result["status"] = "complete"
    write_private_result(args.result, result)
    print("SafeRide Hugging Face public surfaces refreshed and anonymously verified.")


if __name__ == "__main__":
    main()
