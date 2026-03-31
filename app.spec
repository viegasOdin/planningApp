# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec para empacotar o app Streamlit em um executável Windows.
# Use via: pyinstaller app.spec
#
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

# ------------------------------------------------------------
# Coleta todos os arquivos de dados/estáticos do Streamlit
# (CSS, JS, imagens, metadados de componentes, etc.)
# ------------------------------------------------------------
datas = []
datas += copy_metadata("streamlit")
datas += collect_data_files("streamlit")
datas += collect_data_files("altair")
datas += collect_data_files("plotly")
datas += collect_data_files("pyarrow")

# Inclui todos os módulos .py do próprio projeto como dados,
# para que o run_app.py os encontre via sys._MEIPASS
project_py_files = [
    "app.py",
    "absences.py",
    "comparator.py",
    "comparator_geral.py",
    "data_processing.py",
    "data_processing_geral.py",
    "database.py",
    "editor.py",
    "editor_geral.py",
    "editor_matricial.py",
    "editor_matricial_geral.py",
    "utils.py",
    "visualizations.py",
    "visualizations_geral.py",
]
for f in project_py_files:
    if Path(f).exists():
        datas.append((f, "."))

# ------------------------------------------------------------
# Hidden imports — módulos que o PyInstaller não detecta
# automaticamente por serem carregados dinamicamente
# ------------------------------------------------------------
hiddenimports = []
hiddenimports += collect_submodules("streamlit")
hiddenimports += collect_submodules("streamlit.web")
hiddenimports += collect_submodules("streamlit.runtime")
hiddenimports += collect_submodules("streamlit.components")
hiddenimports += [
    # Streamlit internals
    "streamlit.web.cli",
    "streamlit.web.server",
    "streamlit.runtime.scriptrunner",
    "streamlit.runtime.caching",
    "streamlit.runtime.state",
    "streamlit.runtime.uploaded_file_manager",
    # Altair / Vega (renderização de gráficos Altair embutidos no Streamlit)
    "altair",
    "altair.vegalite.v4",
    "toolz",
    "cytoolz",
    # Plotly
    "plotly",
    "plotly.express",
    "plotly.graph_objects",
    "plotly.io",
    # Pandas / NumPy
    "pandas",
    "numpy",
    "pyarrow",
    # SQLAlchemy
    "sqlalchemy",
    "sqlalchemy.dialects.sqlite",
    "sqlalchemy.pool",
    # Openpyxl (leitura de .xlsx)
    "openpyxl",
    "openpyxl.styles",
    "openpyxl.utils",
    # Outros
    "pkg_resources.py2_warn",
    "charset_normalizer",
    "click",
    "tornado",
    "tornado.platform.asyncio",
    "anyio",
    "watchdog",
    "validators",
    "pydeck",
    "PIL",
    "multiprocessing",
]

block_cipher = None

a = Analysis(
    ["run_app.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclui o que não é necessário para reduzir o tamanho do exe
        "tkinter",
        "matplotlib",
        "scipy",
        "IPython",
        "jupyter",
        "notebook",
        "pytest",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # onedir — mais estável com Streamlit
    name="GerenciadorProjetos",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,   # console=True mantém a janela para exibir logs de erro
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="GerenciadorProjetos",
)
