from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from backend.app.database import Database
from scripts.import_synthea import import_synthea


SYNTHEA_ZIP = Path(os.getenv(
    "PRAMANRX_SYNTHEA_ZIP", "data/source/synthea_sample_data_csv_apr2020.zip"
))


class ImporterTestCase(unittest.TestCase):
    @unittest.skipUnless(SYNTHEA_ZIP.exists(), "Synthea fixture ZIP is not available")
    def test_limited_streaming_import_and_fhir_fields(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pramanrx-import-") as raw:
            db = Database(Path(raw) / "import.sqlite")
            counts = import_synthea(SYNTHEA_ZIP, db, limit=2)
            self.assertEqual(counts["patients"], 2)
            patients = db.list_patients(10, 0, None)
            self.assertEqual(len(patients), 2)
            patient = db.get_patient(patients[0]["id"])
            self.assertIn("postalCode", patient["address"])


if __name__ == "__main__":
    unittest.main()
