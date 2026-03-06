import sys
import types


def _install_magic_stub() -> None:
    if "magic" in sys.modules:
        return

    magic_mod = types.ModuleType("magic")

    class _Magic:
        def __init__(self, mime=True, uncompress=True):
            self.mime = mime
            self.uncompress = uncompress

        def from_file(self, path):
            return "application/octet-stream"

    magic_mod.Magic = _Magic
    sys.modules["magic"] = magic_mod


def _install_oras_stub() -> None:
    if "oras.client" in sys.modules:
        return

    oras_mod = types.ModuleType("oras")
    client_mod = types.ModuleType("oras.client")

    class _OrasClient:
        def login(self, hostname, username, password):
            return {"ok": True}

        def pull(self, target, outdir=None):
            return []

        def push(self, ref, data=None, media_type=None):
            return None

        def delete(self, ref):
            return None

        def logout(self):
            return None

    client_mod.OrasClient = _OrasClient
    oras_mod.client = client_mod

    sys.modules["oras"] = oras_mod
    sys.modules["oras.client"] = client_mod


_install_magic_stub()
_install_oras_stub()
