"""AppTest entry for tests: installs a fake auth backend, then runs the real app.py. Never deployed."""
import runpy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crop_yield_explorer import accounts
sys.path.insert(0, str(Path(__file__).parent))
from fake_backend import FakeBackend

if not hasattr(accounts, "_test_be"):
    accounts._test_be = FakeBackend()
    accounts._test_be.add_user("amina@example.com", "GoodPassw0rd!", "Amina Bello")
accounts.set_backend_for_tests(accounts._test_be)
runpy.run_path(str(Path(__file__).resolve().parent.parent / "app.py"), run_name="__main__")
