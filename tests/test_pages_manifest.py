"""Offline checks for public Pages update metadata validation."""
import hashlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from prepare_pages_update import NAMES, REPO, validate


def sha(data):
    return hashlib.sha256(data).hexdigest()


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.hashes = {NAMES[0]: "a" * 64, NAMES[1]: "b" * 64}
        self.sums = "".join(f"{digest}  {name}\r\n" for name, digest in self.hashes.items()).encode()
        self.manifest = {
            "schemaVersion": 1, "product": "CastoriceWish", "version": "0.3.9",
            "tag": "v0.3.9", "repository": REPO, "platform": "windows-x64-portable",
            "signed": False,
            "assets": [{"name": name, "size": 100 + i, "sha256": self.hashes[name]}
                       for i, name in enumerate(NAMES)],
        }
        self.release = {
            "id": 123, "draft": False, "prerelease": False,
            "published_at": "2026-10-25T00:00:00Z", "tag_name": "v0.3.9",
            "assets": [{"name": name, "size": 100 + i, "digest": "sha256:" + self.hashes[name],
                        "state": "uploaded"} for i, name in enumerate(NAMES)],
        }

    def check(self):
        raw = (json.dumps(self.manifest) + "\n").encode()
        remaining = [a for a in self.release["assets"]
                     if a["name"] not in ("update.json", "SHA256SUMS.txt")]
        self.release["assets"] = remaining + [
            {"name": "update.json", "size": len(raw), "digest": "sha256:" + sha(raw), "state": "uploaded"},
            {"name": "SHA256SUMS.txt", "size": len(self.sums),
             "digest": "sha256:" + sha(self.sums), "state": "uploaded"},
        ]
        return validate(self.release, raw, self.sums)

    def test_unsigned_valid(self):
        self.assertEqual(self.check(), "v0.3.9")

    def test_incorrect_tag(self):
        self.manifest["tag"] = "v0.3.8"
        with self.assertRaisesRegex(ValueError, "identity"):
            self.check()

    def test_asset_digest_mismatch(self):
        self.manifest["assets"][0]["sha256"] = "c" * 64
        with self.assertRaisesRegex(ValueError, "does not match"):
            self.check()

    def test_unpublished_blocked(self):
        self.release["draft"] = True
        with self.assertRaisesRegex(ValueError, "not published"):
            self.check()

    def test_missing_signed_asset(self):
        self.manifest["signed"] = True
        with self.assertRaisesRegex(ValueError, "signature asset"):
            self.check()

    def test_checksum_mismatch(self):
        self.sums = self.sums.replace(b"a" * 64, b"c" * 64)
        with self.assertRaisesRegex(ValueError, "Checksums disagree"):
            self.check()


if __name__ == "__main__":
    unittest.main()
