# PyInstaller spec for the bundled HELIOS backend (onedir).
#
# Produces dist/helios-backend/helios-backend[.exe] — a self-contained FastAPI
# server with no system-Python dependency. The optional ML stack
# (torch/transformers/chromadb/sklearn) is intentionally excluded: those
# imports are lazy and guarded throughout the backend, so semantic-search and
# RAG features degrade gracefully while keeping the bundle small and reliable.
import os

from PyInstaller.utils.hooks import collect_all, collect_submodules

here = os.path.abspath(os.getcwd())

hiddenimports: list[str] = []
datas: list = []
binaries: list = []


def _collect_all(pkg: str) -> None:
    try:
        d, b, h = collect_all(pkg)
        datas.extend(d)
        binaries.extend(b)
        hiddenimports.extend(h)
    except Exception:
        pass


# Web stack + lazily-loaded third-party libs (document parsing, crypto, http).
# uvicorn[standard] resolves its loops/protocols dynamically, so collect them.
for _pkg in (
    "uvicorn", "fastapi", "starlette", "pydantic", "pydantic_core",
    "anyio", "click", "h11", "websockets", "httptools", "watchfiles",
    "numpy", "scipy", "pypdf", "openpyxl", "docx",
    "cryptography", "requests", "certifi", "dotenv",
):
    _collect_all(_pkg)

# First-party packages: discover every top-level backend package and pull in all
# submodules, so engines referenced via dynamic/guarded imports still ship.
for _name in sorted(os.listdir(here)):
    _path = os.path.join(here, _name)
    if (
        os.path.isdir(_path)
        and os.path.exists(os.path.join(_path, "__init__.py"))
        and not _name.startswith((".", "_"))
        and _name not in ("tests",)
    ):
        try:
            hiddenimports.extend(collect_submodules(_name))
        except Exception:
            pass


a = Analysis(
    ["helios_server.py"],
    pathex=[here],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "torch", "torchvision", "torchaudio",
        "sentence_transformers", "transformers", "chromadb",
        "sklearn", "onnxruntime", "tensorflow",
        "matplotlib", "tkinter", "PyQt5", "PyQt6", "PySide6",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="helios-backend",
    console=True,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfile,
    a.datas,
    name="helios-backend",
)
