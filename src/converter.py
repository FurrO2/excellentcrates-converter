from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import unicodedata
import uuid
import zipfile
from pathlib import Path
from typing import Any

import yaml


class Dumper(yaml.SafeDumper):
    pass


def represent_str(dumper: yaml.SafeDumper, value: str) -> yaml.ScalarNode:
    style = "'" if "\n" not in value and (not value or value.strip() != value or re.search(r"[:#{}\[\],&*!|>'\"%@`]|^[-?:]\s", value)) else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", value, style=style)


Dumper.add_representer(str, represent_str)


def slug(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value).strip().lower())
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^a-z0-9_-]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_-")
    return text or "converted"


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError("The YAML document must contain an object at its root")
    return data


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data, Dumper=Dumper, allow_unicode=True, sort_keys=False, width=120), encoding="utf-8")


def item_data(block: Any) -> dict[str, Any] | None:
    if not isinstance(block, dict):
        return None
    # Old ExcellentCrates stores serialized Bukkit item data under Provider/Data.
    if "Provider" in block and isinstance(block.get("Data"), dict):
        return block["Data"]
    if "Data" in block and isinstance(block["Data"], dict):
        return block["Data"]
    return None


def new_item(data: Any, provider: Any = "vanilla") -> dict[str, Any] | None:
    if not isinstance(data, dict):
        return None
    return {"Data": data, "Provider": provider or "vanilla"}


def convert_legacy_command(command: Any) -> Any:
    if not isinstance(command, str):
        return command
    # ExcellentCrates v7 uses the separate /cratekey command for key actions.
    return re.sub(r"^(\s*/?)crate\s+key(?=\s|$)", r"\1cratekey", command, count=1, flags=re.IGNORECASE)


def convert_key(old: dict[str, Any]) -> dict[str, Any]:
    item = item_data(old.get("ItemData"))
    legacy_limits = old.get("Limits") or {}
    global_amount = int(legacy_limits.get("GlobalAmount", 0) or 0)
    individual_amount = int(legacy_limits.get("PlayerAmount", 0) or 0)
    global_limit_enabled = bool(legacy_limits.get("Enabled", False)) and global_amount > 0
    individual_limit_enabled = bool(legacy_limits.get("Enabled", False)) and individual_amount > 0
    converted: dict[str, Any] = {
        "base": {"virtual": bool(old.get("Virtual", False))},
        "display": {"name": old.get("Name", ""), "lore": old.get("Description") or []},
        "item": {"stackable": bool(old.get("ItemStackable", True)), "inherit_display_settings": True},
    }
    if item:
        converted["item"]["item"] = new_item(item, (old.get("ItemData") or {}).get("Provider", "vanilla"))
    return converted


def convert_reward(old_id: str, old: dict[str, Any], crate_id: str, report: list[str]) -> tuple[str, dict[str, Any]]:
    reward_id = slug(old_id)
    kind = str(old.get("Type", "")).upper()
    preview = item_data(old.get("PreviewData"))
    legacy_limits = old.get("Limits") or {}
    global_amount = int(legacy_limits.get("GlobalAmount", 0) or 0)
    individual_amount = int(legacy_limits.get("PlayerAmount", 0) or 0)
    global_limit_enabled = bool(legacy_limits.get("Enabled", False)) and global_amount > 0
    individual_limit_enabled = bool(legacy_limits.get("Enabled", False)) and individual_amount > 0
    converted: dict[str, Any] = {
        "base": {"weight": old.get("Weight", 1.0)},
        "preview": {"name": old.get("Name", old_id), "lore": old.get("Description") or [], "use_item_data": True},
        "broadcast": {"enabled": bool(old.get("Broadcast", False))},
        "cooldown": {"global": {"enabled": False, "mode": "DAILY", "value": 0}, "individual": {"enabled": False, "mode": "DAILY", "value": 0}},
        "limit": {"enabled": global_limit_enabled or individual_limit_enabled,
                  "global": {"Enabled": global_limit_enabled, "Amount": global_amount},
                  "individual": {"Enabled": individual_limit_enabled, "Amount": individual_amount},
                  "alternative": {"enabled": False, "reward_id": {"namespace": "none", "value": "none"}}},
        "Rarity": {"enabled": bool(old.get("Rarity")), "rarity_id": slug(old.get("Rarity", "common"))},
    }
    req = old.get("Required_Permissions") or []
    ignored = old.get("Ignored_For_Permissions") or []
    if req or ignored:
        report.append(f"{crate_id}/{old_id}: reward permissions need manual review.")
    limits = old.get("Limits") or {}
    if limits.get("Enabled") and (limits.get("GlobalCooldown", 0) or limits.get("PlayerCooldown", 0)):
        report.append(f"{crate_id}/{old_id}: limit cooldown periods need manual review.")
    if kind == "COMMAND":
        bundle_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{crate_id}/{reward_id}/command_bundle"))
        commands = old.get("Commands") or []
        if not isinstance(commands, list):
            commands = [commands]
        converted["commands"] = {
            "enabled": True,
            "give_mode": "NORMAL",
            "iterations": 1,
            "bundles": {bundle_id: {"commands": [convert_legacy_command(command) for command in commands], "weight": 0.0}},
        }
    elif kind == "ITEM":
        converted["items"] = {"item_list": {}}
        raw_items = old.get("ItemsData") or {}
        first_reward_item: dict[str, Any] | None = None
        for item_key, value in raw_items.items():
            data = item_data(value)
            if data:
                item = new_item(data, (value or {}).get("Provider", "vanilla"))
                if first_reward_item is None:
                    first_reward_item = item
                converted["items"]["item_list"][str(uuid.uuid5(uuid.NAMESPACE_URL, f"{crate_id}/{reward_id}/{item_key}"))] = item
        # Legacy PreviewData is often a decorative player head. The v7 preview
        # should display the actual first item delivered by an ITEM reward.
        if first_reward_item:
            converted["preview"]["icon"] = first_reward_item
        if not converted["items"]["item_list"]:
            report.append(f"{crate_id}/{old_id}: ITEM reward has no usable ItemsData.")
    else:
        report.append(f"{crate_id}/{old_id}: reward type {kind or '(missing)'} is not supported.")
    if "icon" not in converted["preview"] and preview:
        converted["preview"]["icon"] = new_item(preview, (old.get("PreviewData") or {}).get("Provider", "vanilla"))
    if old.get("Custom_Preview") or old.get("Placeholder_Apply"):
        report.append(f"{crate_id}/{old_id}: review Custom_Preview/Placeholder_Apply options manually.")
    return reward_id, converted


def dimension_for_world(world_name: str, world_map: dict[str, str]) -> str:
    if world_name in world_map:
        return world_map[world_name]
    raw_world = world_name.strip().lower()
    if raw_world.startswith("minecraft:"):
        return raw_world
    # In the v7 files supplied by the user, the namespaced key identifies the
    # server world (for example minecraft:world1), not a dimension category.
    return f"minecraft:{slug(world_name)}"


def convert_crate(old: dict[str, Any], crate_id: str, output: Path, report: list[str], world_map: dict[str, str], legacy_config: dict[str, Any]) -> None:
    display_item = item_data(old.get("ItemProvider"))
    effect = (old.get("Block") or {}).get("Effect") or {}
    hologram = (old.get("Block") or {}).get("Hologram") or {}
    templates = (((legacy_config.get("Crate") or {}).get("Holograms") or {}).get("TemplateList") or {})
    template_id = str(hologram.get("Template", "default"))
    template = templates.get(template_id) or templates.get(slug(template_id)) or {}
    hologram_text = template.get("Text") if isinstance(template, dict) else None
    if hologram.get("Enabled") and not hologram_text:
        report.append(f"{crate_id}: hologram template {template_id!r} was not found in config.yml; default text was kept.")
    old_animation = old.get("Animation") or {}
    old_animation_id = str(old_animation.get("Id", "default")).strip().lower()
    animation_profile = "csgo_animation:default" if old_animation_id in {"csgo", "csgo_auto"} else "simple_roll:default"
    if old_animation.get("Enabled") and old_animation_id not in {"", "default", "simple_roll", "csgo", "csgo_auto"}:
        report.append(f"{crate_id}: legacy animation {old_animation_id!r} was replaced with v7 profile {animation_profile}.")
    out: dict[str, Any] = {
        "base": {"permission_required": bool(old.get("Permission_Required", False))},
        "display": {"name": old.get("Name", crate_id), "lore": old.get("Description") or []},
        "item": {"item_stackable": bool(old.get("ItemStackable", True)), "use_display": True},
        "opening": {"enabled": True, "opening_commands": []},
        "hologram": {"enabled": bool(hologram.get("Enabled", False)), "text": hologram_text or ["%crate_name%"], "offset": {"x": 0.0, "y": float(hologram.get("Y_Offset", 0.0) or 0.0) + 0.7, "z": 0.0}},
        "cooldowns": {"global": {"enabled": False, "mode": "DAILY", "value": 0}, "individual": {"enabled": bool((old.get("OpeningCooldown") or {}).get("Enabled", False)), "mode": "DAILY", "value": (old.get("OpeningCooldown") or {}).get("Value", 0)}},
        "animation": {"enabled": bool(old_animation.get("Enabled", False)), "profile": animation_profile},
        "effect": {"enabled": bool(effect.get("Enabled", False)), "profile": f"{str(effect.get('Model', 'helix')).lower()}:default"},
        "key_requirements": {"enabled": False, "keys": {}},
        "preview": {"enabled": bool((old.get("Preview") or {}).get("Enabled", True)), "config": f"inventory:{(old.get('Preview') or {}).get('Id', 'default')}"},
        "rewards": {"required_rewards": 1, "reward_list": {}},
    }
    if display_item:
        out["item"]["item"] = new_item(display_item, (old.get("ItemProvider") or {}).get("Provider", "vanilla"))
    legacy_positions = (old.get("Block") or {}).get("Positions") or old.get("Positions") or []
    converted_positions: dict[str, list[str]] = {}
    for legacy_position in legacy_positions:
        parts = [part.strip() for part in str(legacy_position).split(",")]
        if len(parts) < 4:
            report.append(f"{crate_id}: could not read block position ({legacy_position!r}); place it in-game.")
            continue
        x, y, z, legacy_world = parts[:4]
        world_key = dimension_for_world(legacy_world, world_map)
        try:
            coords = [str(float(value)) for value in (x, y, z)]
        except ValueError:
            report.append(f"{crate_id}: invalid block coordinates ({legacy_position!r}); place them in-game.")
            continue
        converted_positions.setdefault(world_key, []).append(",".join(coords + ["0.0", "0.0"]))
    if converted_positions:
        out["blocks"] = {"positions": converted_positions}

    legacy_costs = old.get("CostOptions") or {}
    key_requirements: dict[str, dict[str, int]] = {}
    unsupported_costs: list[str] = []
    for cost in legacy_costs.values():
        if not isinstance(cost, dict) or not cost.get("Enabled", True):
            continue
        for entry in (cost.get("Entries") or {}).values():
            if not isinstance(entry, dict):
                continue
            if str(entry.get("Type", "")).lower() == "key" and entry.get("Key"):
                key_requirements[str(entry["Key"])] = {"amount": int(entry.get("Amount", 1) or 1)}
            else:
                unsupported_costs.append(str(entry.get("Type", "inconnu")))
    out["key_requirements"] = {"enabled": bool(key_requirements), "keys": key_requirements}
    if unsupported_costs:
        report.append(f"{crate_id}: costs other than keys ({', '.join(sorted(set(unsupported_costs)))}) were not converted.")
    if (old.get("Block") or {}).get("Pushback", {}).get("Enabled"):
        report.append(f"{crate_id}: review the legacy crate's Pushback behavior.")
    rewards = ((old.get("Rewards") or {}).get("List") or {})
    reward_id_map = {str(old_reward_id): slug(old_reward_id) for old_reward_id in rewards}
    seen: set[str] = set()
    for old_reward_id, reward in rewards.items():
        new_id, new_reward = convert_reward(str(old_reward_id), reward or {}, crate_id, report)
        original = new_id
        n = 2
        while new_id in seen:
            new_id = f"{original}_{n}"; n += 1
        seen.add(new_id)
        if new_id != original:
            report.append(f"{crate_id}: ID collision after normalizing {old_reward_id!r}; renamed to {new_id}.")
        write_yaml(output / "objects" / "reward" / crate_id / f"{new_id}.yml", new_reward)
        out["rewards"]["reward_list"][str(uuid.uuid5(uuid.NAMESPACE_URL, f"{crate_id}/{new_id}"))] = {"reward_id": new_id}
    legacy_milestones = old.get("Milestones") or {}
    milestone_entries = legacy_milestones.get("List") or {}
    if milestone_entries:
        converted_milestones: dict[str, Any] = {}
        for old_index, milestone in milestone_entries.items():
            if not isinstance(milestone, dict):
                report.append(f"{crate_id}: could not read milestone {old_index!r}; review the conversion.")
                continue
            old_reward_id = str(milestone.get("Reward_Id", ""))
            new_reward_id = reward_id_map.get(old_reward_id, slug(old_reward_id))
            try:
                openings = int(milestone.get("Openings", old_index))
            except (TypeError, ValueError):
                openings = 0
            if old_reward_id and old_reward_id not in reward_id_map:
                report.append(f"{crate_id}: milestone {openings} references missing reward {old_reward_id!r}; review reward_id: {new_reward_id}.")
            milestone_uuid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{crate_id}/milestone/{openings}/{new_reward_id}"))
            converted_milestones[milestone_uuid] = {"reward_id": new_reward_id, "openings": openings}
        out["milestones"] = {
            "enabled": bool(converted_milestones),
            "repeatable": bool(legacy_milestones.get("Repeatable", False)),
            "milestone_list": converted_milestones,
        }
    write_yaml(output / "objects" / "crate" / f"{crate_id}.yml", out)


def source_from_archive(source: Path, temp: Path) -> Path:
    if source.is_dir():
        return source
    if source.suffix.lower() != ".zip":
        raise ValueError("The source must be an ExcellentCrates folder or a .zip archive")
    temp.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source) as archive:
        for member in archive.infolist():
            target = (temp / member.filename).resolve()
            if temp.resolve() not in target.parents and target != temp.resolve():
                raise ValueError(f"Chemin invalide dans l'archive: {member.filename}")
        archive.extractall(temp)
    return temp


def convert(source_arg: Path, destination: Path, world_map: dict[str, str] | None = None) -> dict[str, Any]:
    temp = destination.parent / f".{destination.name}-source"
    if temp.exists():
        shutil.rmtree(temp)
    source = source_from_archive(source_arg, temp)
    legacy_config_path = source / "config.yml"
    legacy_config = load_yaml(legacy_config_path) if legacy_config_path.is_file() else {}
    crates_dir, keys_dir = source / "crates", source / "keys"
    if not crates_dir.is_dir() and not keys_dir.is_dir():
        raise ValueError("No crates/ or keys/ folder was found in the source")
    destination.mkdir(parents=True, exist_ok=True)
    report: list[str] = []
    world_map = world_map or {}
    converted_crates = converted_keys = 0
    used_crate_ids: set[str] = set()
    for path in sorted(crates_dir.glob("*.yml")) if crates_dir.is_dir() else []:
        crate_id = slug(path.stem)
        base_id = crate_id
        suffix = 2
        while crate_id in used_crate_ids:
            crate_id = f"{base_id}_{suffix}"
            suffix += 1
        used_crate_ids.add(crate_id)
        if crate_id != base_id:
            report.append(f"{path.name}: ID collision after normalization; crate renamed to {crate_id}.")
        try:
            convert_crate(load_yaml(path), crate_id, destination, report, world_map, legacy_config)
            converted_crates += 1
        except Exception as exc:
            report.append(f"{path.name}: erreur de lecture/conversion: {exc}")
    used_key_ids: set[str] = set()
    for path in sorted(keys_dir.glob("*.yml")) if keys_dir.is_dir() else []:
        key_id = slug(path.stem)
        base_id = key_id
        suffix = 2
        while key_id in used_key_ids:
            key_id = f"{base_id}_{suffix}"
            suffix += 1
        used_key_ids.add(key_id)
        if key_id != base_id:
            report.append(f"{path.name}: ID collision after normalization; key renamed to {key_id}.")
        try:
            converted = convert_key(load_yaml(path))
            write_yaml(destination / "objects" / "key" / f"{key_id}.yml", converted)
            converted_keys += 1
        except Exception as exc:
            report.append(f"{path.name}: erreur de lecture/conversion: {exc}")
    report.extend([
        "data.db is not modified or migrated by this tool.",
        "Config, language, menus, custom animations, and history files are not migrated.",
        "Check converted crates and rewards in-game before using these files on a server.",
    ])
    result = {
        "output_folder": destination.name,
        "crates_converted": converted_crates,
        "keys_converted": converted_keys,
        "rewards_folder": "objects/reward/<crate_id>/",
        "milestones": "objects/crate/<crate_id>.yml -> milestones.milestone_list",
        "warnings": report,
    }
    (destination / "conversion-report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (destination / "manifest.json").write_text(json.dumps({
        "load_order": ["objects/key/", "objects/reward/", "objects/crate/"],
        "crates": sorted(p.stem for p in (destination / "objects" / "crate").glob("*.yml")),
        "keys": sorted(p.stem for p in (destination / "objects" / "key").glob("*.yml")),
        "note": "Rewards are referenced by crates; milestones point to those same reward IDs.",
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    if source_arg.is_file() and temp.exists():
        shutil.rmtree(temp)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert legacy ExcellentCrates YAML configurations to the v7 structure.")
    parser.add_argument("source", type=Path, help="ExcellentCrates plugin folder or ZIP archive")
    parser.add_argument("destination", type=Path, nargs="?", default=Path("excellentcrates [converted]"), help="Output folder (default: excellentcrates [converted])")
    parser.add_argument("--world-map", action="append", default=[], metavar="OLD=NEW", help="Map a legacy world name to a target identifier, e.g. survival=minecraft:overworld")
    args = parser.parse_args()
    if args.destination.exists() and any(args.destination.iterdir()):
        parser.error("The destination folder must be empty to avoid overwriting files")
    try:
        world_map = {}
        for mapping in args.world_map:
            if "=" not in mapping:
                parser.error(f"Invalid world mapping: {mapping}")
            old_world, new_world = mapping.split("=", 1)
            world_map[old_world] = new_world
        result = convert(args.source, args.destination, world_map)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    print(f"Conversion complete: {result['crates_converted']} crates, {result['keys_converted']} keys.")
    print(f"Report: {args.destination / 'conversion-report.json'}")
    print(f"Warnings: {len(result['warnings'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
