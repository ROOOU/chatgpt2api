import json
import tempfile
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
ROOT_CONFIG_FILE = ROOT_DIR / "config.json"


class ConfigLoadingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._created_root_config = False
        if not ROOT_CONFIG_FILE.exists():
            ROOT_CONFIG_FILE.write_text(json.dumps({"auth-key": "test-auth"}), encoding="utf-8")
            cls._created_root_config = True

        from services import config as config_module

        cls.config_module = config_module

    @classmethod
    def tearDownClass(cls) -> None:
        if cls._created_root_config and ROOT_CONFIG_FILE.exists():
            ROOT_CONFIG_FILE.unlink()

    def test_load_settings_ignores_directory_config_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir = Path(tmp_dir)
            data_dir = base_dir / "data"
            config_dir = base_dir / "config.json"
            os_auth_key = "env-auth"

            config_dir.mkdir()

            module = self.config_module
            old_base_dir = module.BASE_DIR
            old_data_dir = module.DATA_DIR
            old_config_file = module.CONFIG_FILE
            old_env_auth_key = module.os.environ.get("CHATGPT2API_AUTH_KEY")
            try:
                module.BASE_DIR = base_dir
                module.DATA_DIR = data_dir
                module.CONFIG_FILE = config_dir
                module.os.environ["CHATGPT2API_AUTH_KEY"] = os_auth_key

                settings = module._load_settings()

                self.assertEqual(settings.auth_key, os_auth_key)
                self.assertEqual(settings.refresh_account_interval_minute, 5)
            finally:
                module.BASE_DIR = old_base_dir
                module.DATA_DIR = old_data_dir
                module.CONFIG_FILE = old_config_file
                if old_env_auth_key is None:
                    module.os.environ.pop("CHATGPT2API_AUTH_KEY", None)
                else:
                    module.os.environ["CHATGPT2API_AUTH_KEY"] = old_env_auth_key

    def test_default_text_model_prefers_env_and_replaces_auto(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "config.json"
            path.write_text(json.dumps({"auth-key": "test-auth", "default_text_model": "gpt-5"}), encoding="utf-8")
            module = self.config_module
            old_env_model = module.os.environ.get("CHATGPT2API_DEFAULT_TEXT_MODEL")
            try:
                module.os.environ["CHATGPT2API_DEFAULT_TEXT_MODEL"] = "gpt-5-5"
                store = module.ConfigStore(path)

                self.assertEqual(store.default_text_model, "gpt-5-5")
                self.assertEqual(store.text_model_or_default(None), "gpt-5-5")
                self.assertEqual(store.text_model_or_default("auto"), "gpt-5-5")
                self.assertEqual(store.text_model_or_default("gpt-5-3"), "gpt-5-3")
            finally:
                if old_env_model is None:
                    module.os.environ.pop("CHATGPT2API_DEFAULT_TEXT_MODEL", None)
                else:
                    module.os.environ["CHATGPT2API_DEFAULT_TEXT_MODEL"] = old_env_model


if __name__ == "__main__":
    unittest.main()
