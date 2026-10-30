# SPDX-License-Identifier: MIT
"""Adapt the existing pure package reader without loading its Unreal module.

Only its literal constants, exception and two pure functions are compiled. This
keeps package-format validation in one implementation and never evaluates the
importer's top-level Unreal import, CLI, fetch or native functions.
"""

import ast
import builtins
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath
import stat
import struct
import zipfile

from .glb_payload import PayloadError, validate_glb
from .archive_integrity import ArchiveIntegrityError, validate_archive_integrity

MAX_PACKAGE_BYTES = 64 * 1024 * 1024
MAX_EXPANDED_BYTES = 256 * 1024 * 1024
MAX_MEMBERS = 4096
IMPORTER = (Path(__file__).resolve().parents[2] / "engines" / "unreal" /
            "DaedalusLink" / "Content" / "Python" / "import_world_package.py")


class PlanError(ValueError):
    """Input cannot safely produce an offline preservation plan."""


def strict_json(data):
    """Reject ambiguous object keys and non-JSON NaN/Infinity values."""
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise PlanError("duplicate JSON key: " + key)
            result[key] = value
        return result

    def constant(value):
        raise PlanError("nonfinite JSON number: " + value)

    def floating(value):
        if len(value) > 128:
            raise PlanError("JSON floating-point token exceeds offline budget")
        number = float(value)
        if not math.isfinite(number):
            raise PlanError("nonfinite JSON number: " + value)
        return number

    def integer(value):
        if len(value.lstrip("-")) > 64:
            raise PlanError("JSON integer token exceeds offline budget")
        return int(value)

    try:
        return json.loads(data, object_pairs_hook=pairs, parse_constant=constant,
                          parse_float=floating, parse_int=integer)
    except (UnicodeError, ValueError, RecursionError) as error:
        raise PlanError("invalid JSON: " + str(error)) from error


def _reader():
    """Compile the existing reader's pure boundary, refusing changed signatures."""
    try:
        tree = ast.parse(IMPORTER.read_text(encoding="utf-8"), filename=str(IMPORTER))
        selected = []
        counts = {}
        signatures = {"glb_summary": ["data"], "read_package": ["zip_path"]}
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                if isinstance(target, ast.Name) and target.id in ("FORMAT", "VERSION"):
                    ast.literal_eval(node.value)
                    selected.append(node)
                    counts[target.id] = counts.get(target.id, 0) + 1
            if isinstance(node, ast.ClassDef) and node.name == "PackageError":
                if (node.decorator_list or node.keywords or len(node.bases) != 1 or
                        not isinstance(node.bases[0], ast.Name) or node.bases[0].id != "Exception" or
                        any(not isinstance(item, ast.Expr) or
                            not isinstance(item.value, ast.Constant) or
                            not isinstance(item.value.value, str) for item in node.body)):
                    raise PlanError("existing PackageError contract changed")
                selected.append(node)
                counts[node.name] = counts.get(node.name, 0) + 1
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in signatures:
                args = node.args
                if (not isinstance(node, ast.FunctionDef) or node.decorator_list or node.returns or
                        args.defaults or args.kw_defaults or args.posonlyargs or args.kwonlyargs or
                        args.vararg or args.kwarg or
                        [arg.arg for arg in args.args] != signatures[node.name] or
                        any(arg.annotation for arg in args.args) or
                        any(isinstance(item, (ast.Import, ast.ImportFrom)) for item in ast.walk(node))):
                    raise PlanError("existing pure reader signature changed: " + node.name)
                selected.append(node)
                counts[node.name] = counts.get(node.name, 0) + 1
        if counts != {name: 1 for name in ("FORMAT", "VERSION", "PackageError", "glb_summary", "read_package")}:
            raise PlanError("existing pure package reader is missing or ambiguous")
        namespace = {"__name__": "_daedalus_offline_package_reader", "json": json,
                     "struct": struct, "zipfile": zipfile,
                     "__builtins__": {"__build_class__": builtins.__build_class__,
                                      "Exception": Exception, "len": len}}
        exec(compile(ast.Module(body=selected, type_ignores=[]), str(IMPORTER), "exec"), namespace)
        if namespace["FORMAT"] != "daedalus-world-package" or type(namespace["VERSION"]) is not int or namespace["VERSION"] != 1:
            raise PlanError("existing package reader version changed; review the adapter")
        return namespace
    except (OSError, SyntaxError, TypeError, ValueError, NameError) as error:
        raise PlanError("cannot load existing pure package reader: " + str(error)) from error


def member_path(name):
    """Require a portable relative ZIP file name; no extraction is performed."""
    if not isinstance(name, str) or not name or len(name) > 512:
        raise PlanError("invalid ZIP member name")
    path = PurePosixPath(name)
    parts = name.split("/")
    if (path.is_absolute() or any(char in name for char in '\\:<>"|?*') or
            any(part in ("", ".", "..") or part.endswith((".", " ")) for part in parts) or
            any(ord(char) < 32 or ord(char) == 127 for char in name)):
        raise PlanError("unsafe ZIP member: " + name)
    reserved = {"CON", "PRN", "AUX", "NUL"} | {"COM" + str(n) for n in range(1, 10)} | {"LPT" + str(n) for n in range(1, 10)}
    if any(part.split(".")[0].upper() in reserved for part in parts):
        raise PlanError("nonportable ZIP member: " + name)
    return name


def read_snapshot(zip_path):
    """Read one bounded immutable byte snapshot, validate it, return manifest/hash."""
    try:
        with Path(zip_path).open("rb") as stream:
            data = stream.read(MAX_PACKAGE_BYTES + 1)
        if len(data) > MAX_PACKAGE_BYTES:
            raise PlanError("package exceeds 64 MiB offline input budget")
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            if len(entries) > MAX_MEMBERS or sum(entry.file_size for entry in entries) > MAX_EXPANDED_BYTES:
                raise PlanError("ZIP exceeds offline member/expanded-byte budget")
            seen = set()
            for entry in entries:
                # Server packages contain files only. Refuse directories/symlinks
                # instead of guessing what a later native adopter would extract.
                member_path(entry.filename)
                if entry.orig_filename != entry.filename:
                    raise PlanError("ambiguous ZIP member name")
                mode = entry.external_attr >> 16
                if entry.is_dir() or (stat.S_IFMT(mode) not in (0, stat.S_IFREG)) or entry.flag_bits & 1:
                    raise PlanError("unsupported ZIP member type: " + entry.filename)
                folded = entry.filename.casefold()
                if folded in seen:
                    raise PlanError("duplicate or case-colliding ZIP member: " + entry.filename)
                seen.add(folded)
            for name in seen:
                parts = name.split("/")
                if any("/".join(parts[:count]) in seen for count in range(1, len(parts))):
                    raise PlanError("ZIP member file/directory prefix collision: " + name)
            try:
                validate_archive_integrity(archive, max_expanded_bytes=MAX_EXPANDED_BYTES,
                                           max_member_bytes=MAX_EXPANDED_BYTES)
            except ArchiveIntegrityError as error:
                raise PlanError(str(error)) from error

            def read_member(name):
                try:
                    # Reading to EOF evaluates CRC and decompressor errors;
                    # each member is already covered by the expansion budget.
                    return archive.read(name)
                except Exception as error:
                    raise PlanError(name + ": cannot read ZIP member: " + str(error)) from error

            manifest = strict_json(read_member("manifest.json").decode("utf-8"))
            if not isinstance(manifest, dict):
                raise PlanError("manifest must be an object")
            reader = _reader()
            names = archive.namelist()
            payloads = ["world.glb"]
            assets = manifest.get("assets", [])
            if not isinstance(assets, list):
                raise PlanError("manifest assets must be an array")
            for asset in assets:
                if not isinstance(asset, dict):
                    raise PlanError("each asset must be an object")
                name = member_path(asset.get("file"))
                if name not in names or not name.startswith("assets/") or not name.endswith(".glb"):
                    raise PlanError(name + ": asset.file must name an existing assets/*.glb member")
                if name not in payloads:
                    payloads.append(name)
            for name in payloads:
                try:
                    validate_glb(read_member(name), name, reader["glb_summary"], strict_json)
                except PayloadError as error:
                    raise PlanError(str(error)) from error
            try:
                checked, _, names = reader["read_package"](io.BytesIO(data))
            except reader["PackageError"] as error:
                raise PlanError(str(error)) from error
            if checked != manifest:
                raise PlanError("existing reader and strict manifest disagree")
        return manifest, names, hashlib.sha256(data).hexdigest(), len(data)
    except PlanError:
        raise
    except (OSError, ValueError, KeyError, TypeError, AttributeError, UnicodeError, NameError, RecursionError,
            RuntimeError, NotImplementedError, EOFError, struct.error, zipfile.BadZipFile) as error:
        raise PlanError("cannot read package: " + str(error)) from error
