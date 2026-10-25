#!/usr/bin/env python3
"""Stage an unchanged, validated update.json from the latest stable public Release."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.request import Request, urlopen

REPO = "sirarikako/CastoriceWish.Releases"
API = f"https://api.github.com/repos/{REPO}"
NAMES = ("CastoriceWish-Portable.exe", "CastoriceWish-Portable.zip")
SHA = re.compile(r"[a-f0-9]{64}\Z")
TAG = re.compile(r"v\d+\.\d+\.\d+\Z")


def require(ok, message):
    if not ok:
        raise ValueError(message)


def fetch(url, token=None, accept="application/vnd.github+json", limit=128 * 1024):
    headers = {"User-Agent": "CastoriceWish-Pages-Deploy", "Accept": accept}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        headers["X-GitHub-Api-Version"] = "2022-11-28"
    with urlopen(Request(url, headers=headers), timeout=25) as response:
        require(response.status == 200, f"Unexpected HTTP status: {response.status}")
        data = response.read(limit + 1)
    require(len(data) <= limit, "Response exceeds size limit")
    return data


def parse_json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f"Duplicate JSON field: {key}")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique)


def validate(release, update_bytes, sums_bytes):
    require(isinstance(release, dict), "Invalid Release")
    require(release.get("draft") is False and release.get("prerelease") is False
            and release.get("published_at"), "Release is not published and stable")
    tag = release.get("tag_name")
    require(isinstance(tag, str) and TAG.fullmatch(tag), "Invalid Release tag")
    files = release.get("assets")
    require(isinstance(files, list) and all(isinstance(x, dict) for x in files), "Invalid assets")
    by_name = {x.get("name"): x for x in files}
    required = (*NAMES, "SHA256SUMS.txt", "update.json")
    require(len(by_name) == len(files) and all(name in by_name for name in required),
            "Required Release assets missing or duplicated")
    for name in required:
        require(by_name[name].get("state") == "uploaded", f"Asset not uploaded: {name}")
    require(len(update_bytes) == by_name["update.json"].get("size"), "Manifest size mismatch")
    require("sha256:" + hashlib.sha256(update_bytes).hexdigest()
            == by_name["update.json"].get("digest"), "Manifest digest mismatch")
    require(len(sums_bytes) == by_name["SHA256SUMS.txt"].get("size"), "Checksums size mismatch")
    require("sha256:" + hashlib.sha256(sums_bytes).hexdigest()
            == by_name["SHA256SUMS.txt"].get("digest"), "Checksums digest mismatch")
    m = parse_json(update_bytes)
    require(isinstance(m, dict), "Manifest must be an object")
    require(type(m.get("schemaVersion")) is int and m["schemaVersion"] == 1,
            "Unsupported manifest schema")
    require(m.get("product") == "CastoriceWish" and m.get("version") == tag[1:]
            and m.get("tag") == tag and m.get("repository") == REPO
            and m.get("platform") == "windows-x64-portable", "Manifest identity mismatch")
    require(type(m.get("signed")) is bool, "Manifest signing state missing")
    require(isinstance(m.get("assets"), list) and len(m["assets"]) == 2,
            "Manifest must list exactly the portable EXE and ZIP")
    seen = set()
    for item in m["assets"]:
        require(isinstance(item, dict), "Malformed manifest asset")
        name = item.get("name")
        require(name in NAMES and name not in seen, "Unexpected or duplicate manifest asset")
        seen.add(name)
        size, digest = item.get("size"), item.get("sha256")
        require(type(size) is int and size > 0 and isinstance(digest, str)
                and SHA.fullmatch(digest), f"Invalid asset size or SHA-256: {name}")
        require(size == by_name[name].get("size") and "sha256:" + digest == by_name[name].get("digest"),
                f"Release asset does not match manifest: {name}")
    require(seen == set(NAMES), "Expected portable files not listed")
    if m["signed"]:
        require(by_name.get("app-update.signed.json", {}).get("state") == "uploaded",
                "Signed Release is missing its signature asset")
    checksum_lines = sums_bytes.decode("utf-8-sig").splitlines()
    checksum_map = {}
    for line in checksum_lines:
        if not line.strip():
            continue
        match = re.fullmatch(r"([a-fA-F0-9]{64})\s+([^/\\\s]+)", line.strip())
        require(match is not None and match.group(2) not in checksum_map, "Invalid SHA256SUMS.txt")
        checksum_map[match.group(2)] = match.group(1).lower()
    require(set(checksum_map) == set(NAMES), "SHA256SUMS.txt asset list mismatch")
    for item in m["assets"]:
        require(checksum_map[item["name"]] == item["sha256"], "Checksums disagree with manifest")
    return tag


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--expected-release-id", default="")
    args = parser.parse_args()
    token = os.environ.get("GH_TOKEN")
    require(token, "Missing GH_TOKEN")
    release = parse_json(fetch(f"{API}/releases/latest", token))
    require(isinstance(release, dict), "Unexpected latest Release payload")
    if args.expected_release_id:
        require(str(release.get("id")) == args.expected_release_id,
                "A newer stable Release exists; refusing to publish stale metadata")
    files = release.get("assets", [])
    require(isinstance(files, list), "Invalid asset response")
    assets = {item.get("name"): item for item in files if isinstance(item, dict)}
    tag = release.get("tag_name")
    require(isinstance(tag, str) and TAG.fullmatch(tag), "Invalid latest tag")
    def read_asset(name, limit):
        item = assets.get(name)
        require(item is not None, f"Missing asset: {name}")
        expected_url = f"https://github.com/{REPO}/releases/download/{tag}/{name}"
        require(item.get("browser_download_url") == expected_url,
                f"Unexpected asset URL: {name}")
        return fetch(expected_url, limit=limit, accept="application/octet-stream")
    update = read_asset("update.json", 64 * 1024)
    sums = read_asset("SHA256SUMS.txt", 8 * 1024)
    validate(release, update, sums)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "update.json").write_bytes(update)  # preserve the publisher's exact bytes
    (args.out / ".nojekyll").write_text("", encoding="utf-8")
    (args.out / "index.html").write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<title>CastoriceWish Updates</title><body><p>CastoriceWish update metadata: '
        '<a href="update.json">update.json</a></p></body></html>\n', encoding="utf-8")
    print(f"Validated {tag}; staged original update.json (no signature policy changes)")
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as output:
            output.write(f"release_id={release['id']}\n")
            output.write(f"tag={tag}\n")


if __name__ == "__main__":
    main()
