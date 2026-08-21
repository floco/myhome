# packages/backend/src/myhome/attachment_modules.py
"""Per-module adapters for the generic attachment machinery: how to find an
item within a module's document (and persist it back), paired with that
module's attachment storage/thumbnail functions. Shared by the generic
attachments REST routes (routes/attachments.py) and the MCP attachment tools
(mcp_tools_attachments.py) so both use the exact same per-module wiring
instead of two separate copies."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import persistence_build as _bld
from . import persistence_chores as _chr
from . import persistence_costs as _cst
from . import persistence_insurance as _ins
from . import persistence_inventory as _inv
from . import persistence_kb as _kb
from . import persistence_locations as _loc
from . import persistence_properties as _prop
from . import persistence_works as _wrk

Finder = Callable[[str, str], tuple[object | None, Callable[[], None]]]


@dataclass
class ModuleAdapter:
    find: Finder
    save_attachment: Callable[[str, str, str, bytes], None]
    get_attachment_path: Callable[[str, str, str], Path]
    delete_attachment: Callable[[str, str, str], bool]
    generate_pdf_thumbnail: Callable[[Path, Path], None]


def _inventory_find(home_id: str, item_id: str):
    doc = _inv.load_inventory(home_id)
    item = next((i for i in doc.items if i.id == item_id), None)
    return item, (lambda: _inv.save_inventory(home_id, doc))


def _kb_find(home_id: str, item_id: str):
    entry = _kb.load_entry(home_id, item_id)
    if entry is None:
        return None, (lambda: None)

    def _save() -> None:
        entry.updatedAt = datetime.now(timezone.utc).isoformat()
        _kb.save_entry(home_id, entry)

    return entry, _save


def _works_find(home_id: str, item_id: str):
    doc = _wrk.load_works(home_id)
    item = next((w for w in doc.works if w.id == item_id), None)
    return item, (lambda: _wrk.save_works(home_id, doc))


def _costs_find(home_id: str, item_id: str):
    doc = _cst.load_costs(home_id)
    item = next((e for e in doc.entries if e.id == item_id), None)
    return item, (lambda: _cst.save_costs(home_id, doc))


def _properties_find(home_id: str, item_id: str):
    doc = _prop.load_properties(home_id)
    item = next((p for p in doc.properties if p.id == item_id), None)
    return item, (lambda: _prop.save_properties(home_id, doc))


def _build_find(home_id: str, item_id: str):
    doc = _bld.load_build(home_id)
    item = next((t for t in doc.tasks if t.id == item_id), None)
    return item, (lambda: _bld.save_build(home_id, doc))


def _chores_find(home_id: str, item_id: str):
    doc = _chr.load_chores(home_id)
    item = next((c for c in doc.chores if c.id == item_id), None)
    return item, (lambda: _chr.save_chores(home_id, doc))


def _insurance_find(home_id: str, item_id: str):
    doc = _ins.load_insurance(home_id)
    item = next((p for p in doc.policies if p.id == item_id), None)
    return item, (lambda: _ins.save_insurance(home_id, doc))


def _locations_find(home_id: str, item_id: str):
    doc = _loc.load_locations(home_id)
    item = next((l for l in doc.locations if l.id == item_id), None)
    return item, (lambda: _loc.save_locations(home_id, doc))


MODULES: dict[str, ModuleAdapter] = {
    "inventory": ModuleAdapter(
        _inventory_find, _inv.save_attachment, _inv.get_attachment_path,
        _inv.delete_attachment, _inv.generate_pdf_thumbnail,
    ),
    "kb": ModuleAdapter(
        _kb_find, _kb.save_attachment, _kb.get_attachment_path,
        _kb.delete_attachment, _kb.generate_pdf_thumbnail,
    ),
    "works": ModuleAdapter(
        _works_find, _wrk.save_attachment, _wrk.get_attachment_path,
        _wrk.delete_attachment, _wrk.generate_pdf_thumbnail,
    ),
    "costs": ModuleAdapter(
        _costs_find, _cst.save_attachment, _cst.get_attachment_path,
        _cst.delete_attachment, _cst.generate_pdf_thumbnail,
    ),
    "properties": ModuleAdapter(
        _properties_find, _prop.save_attachment, _prop.get_attachment_path,
        _prop.delete_attachment, _prop.generate_pdf_thumbnail,
    ),
    "build": ModuleAdapter(
        _build_find, _bld.save_attachment, _bld.get_attachment_path,
        _bld.delete_attachment, _bld.generate_pdf_thumbnail,
    ),
    "chores": ModuleAdapter(
        _chores_find, _chr.save_attachment, _chr.get_attachment_path,
        _chr.delete_attachment, _chr.generate_pdf_thumbnail,
    ),
    "insurance": ModuleAdapter(
        _insurance_find, _ins.save_attachment, _ins.get_attachment_path,
        _ins.delete_attachment, _ins.generate_pdf_thumbnail,
    ),
    "locations": ModuleAdapter(
        _locations_find, _loc.save_attachment, _loc.get_attachment_path,
        _loc.delete_attachment, _loc.generate_pdf_thumbnail,
    ),
}


def get_adapter(module: str) -> ModuleAdapter:
    adapter = MODULES.get(module)
    if adapter is None:
        raise ValueError(f"Unknown module {module!r}. Valid modules: {sorted(MODULES)}")
    return adapter
