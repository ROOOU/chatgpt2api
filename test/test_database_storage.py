from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sqlalchemy import Text

from services.storage.database_storage import AccountModel, DatabaseStorageBackend


class DatabaseStorageTests(unittest.TestCase):
    def test_account_access_token_column_is_unbounded_text(self) -> None:
        self.assertIsInstance(AccountModel.__table__.c.access_token.type, Text)

    def test_round_trips_long_access_token(self) -> None:
        long_token = "token-" + ("x" * 5000)
        with tempfile.TemporaryDirectory() as tmp_dir:
            database_url = f"sqlite:///{Path(tmp_dir) / 'accounts.db'}"
            storage = DatabaseStorageBackend(database_url)

            storage.save_accounts([
                {
                    "access_token": long_token,
                    "type": "Plus",
                    "status": "正常",
                    "quota": 1,
                }
            ])

            self.assertEqual(storage.load_accounts()[0]["access_token"], long_token)


if __name__ == "__main__":
    unittest.main()
