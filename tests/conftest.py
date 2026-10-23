"""Configuracion compartida de pytest para el monorepo SIOC EPS Ilo.

Asegura que la raiz del repositorio este en ``sys.path`` para que los tests
puedan importar el paquete ``src`` sin necesidad de instalar el proyecto.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
