import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.config import load_environment


class ConfigEnvironmentLoadingTest(unittest.TestCase):
    def test_load_environment_reads_project_root_env_when_backend_env_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            backend_dir = project_root / "backend"
            backend_dir.mkdir()
            (project_root / ".env").write_text(
                "DB_URL=mongodb://root-env.example/\n",
                encoding="utf-8",
            )

            with patch.dict(os.environ, {}, clear=True):
                load_environment(backend_dir)

                self.assertEqual(
                    os.environ["DB_URL"],
                    "mongodb://root-env.example/",
                )


if __name__ == "__main__":
    unittest.main()
