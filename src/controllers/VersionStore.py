import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from src.controllers.ScenarioPackage import ScenarioPackage
from src.dto.OperationResult import OperationResult
from src.models.SimulationClock import format_iso_utc

_NAME_RULE = re.compile(r"^[\w\- ]{1,40}$")  # letters, digits, space, _ and -: safe as a file name


@dataclass
class VersionInfo:
    name: str
    saved_at: str


class VersionStore:
    """Named versions that survive closing the program (section 13).
    One JSON file per version, holding the same operational state as the structural export
    (ScenarioPackage). It does NOT hold the undo stack or other versions. Restoring goes through
    ScenarioPackage.apply, so it is validated all-or-nothing and is ONE undoable action."""

    def __init__(self, directory, package=None, now=None):
        self.directory = Path(directory)  # chosen by the caller: no path is fixed in the code
        self.package = package or ScenarioPackage()
        self.now = now or (lambda: datetime.now(timezone.utc))

    def save(self, scenery, name) -> OperationResult:
        error = self._check_name(name)
        if error:
            return OperationResult(False, error)
        path = self._path(name)
        if path.exists():
            return OperationResult(False, f"Ya existe una versión llamada '{name.strip()}'.")
        document = {"tipo": "VERSION", "nombre": name.strip(), "guardada": format_iso_utc(self.now()),
                    "escenario": self.package.export(scenery)}
        self.directory.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")  # write fully, then swap: a crash never leaves a half file
        with open(temporary, "w", encoding="utf-8") as f:
            json.dump(document, f, indent=2, ensure_ascii=False)
        os.replace(temporary, path)
        return OperationResult(True, f"Versión '{name.strip()}' guardada.")

    def list(self) -> list:
        """Saved versions, oldest first. Unreadable files are skipped, never fatal."""
        versions = []
        for path in self.directory.glob("version_*.json") if self.directory.is_dir() else []:
            document = self._read(path)
            if isinstance(document, dict) and isinstance(document.get("nombre"), str):
                versions.append(VersionInfo(document["nombre"], str(document.get("guardada", ""))))
        return sorted(versions, key=lambda v: (v.saved_at, v.name))

    def restore(self, scenery, name) -> OperationResult:
        error = self._check_name(name)
        if error:
            return OperationResult(False, error)
        document = self._read(self._path(name))
        if not isinstance(document, dict) or document.get("tipo") != "VERSION":
            return OperationResult(False, f"No existe la versión '{name.strip()}' o no se puede leer.")
        parsed = self.package.parse(document.get("escenario"))  # nothing is touched if this fails
        if not parsed.success:
            return OperationResult(False, "La versión está dañada: " + " | ".join(parsed.errors[:3]))
        self.package.apply(scenery, parsed.state)
        return OperationResult(True, f"Versión '{name.strip()}' restaurada.")

    def _path(self, name) -> Path:
        # casefold: names that differ only in case would collide on Windows anyway.
        # The "version_" prefix avoids reserved Windows file names such as CON or NUL.
        return self.directory / f"version_{name.strip().casefold()}.json"

    @staticmethod
    def _check_name(name):
        if not isinstance(name, str) or not _NAME_RULE.match(name.strip() or "/"):
            return "El nombre debe tener entre 1 y 40 caracteres: letras, números, espacios, '_' o '-'."
        return None

    @staticmethod
    def _read(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return None