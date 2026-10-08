from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from backend.app.config import PROJECT_ROOT
from backend.app.kb import KnowledgeBaseError, load_verified_kb
from scripts.compile_kb import verify_sources


SOURCE_ROOT = Path(os.getenv("PRAMANRX_KB_SOURCE", PROJECT_ROOT / "data/source/kb"))


class KnowledgeBaseTestCase(unittest.TestCase):
    def test_compiled_kb_signature_and_schema(self) -> None:
        compiled = PROJECT_ROOT / "data/compiled"
        kb = load_verified_kb(
            compiled / "kb-v1.json", compiled / "kb-v1.sig", compiled / "pramanrx-ed25519-public.pem"
        )
        self.assertEqual(kb.version, "2026.10.06-prototype.1")
        self.assertEqual(len(kb.medications), 9)
        self.assertIsNotNone(kb.interaction("warfarin", "ibuprofen"))

    def test_bad_signature_fails_closed(self) -> None:
        compiled = PROJECT_ROOT / "data/compiled"
        with tempfile.TemporaryDirectory(prefix="pramanrx-sig-") as raw:
            signature = Path(raw) / "bad.sig"
            signature.write_bytes(b"invalid")
            with self.assertRaises(KnowledgeBaseError):
                load_verified_kb(compiled / "kb-v1.json", signature,
                                 compiled / "pramanrx-ed25519-public.pem")

    @unittest.skipUnless(SOURCE_ROOT.exists(), "Verified source package is not available")
    def test_source_snapshot_checksums(self) -> None:
        checksums = verify_sources(SOURCE_ROOT)
        self.assertGreater(len(checksums), 30)


if __name__ == "__main__":
    unittest.main()
