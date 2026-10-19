# ExcellentCrates v6 to v7 Converter

A Windows app for converting legacy ExcellentCrates configurations to the v7 object format. This independent project is not affiliated with the ExcellentCrates developers.

## Windows app

Download `ExcellentCrates-Converter.exe` from [Releases](https://github.com/FurrO2/excellentcrates-converter/releases) and open it. Python is not required.

1. On the left, choose the complete legacy plugin ZIP archive or its root folder containing `crates/` and `keys/`.
2. On the right, choose where to create the converted output.
3. Click **Convert to v7**.
4. Back up your v7 plugin folder. Copy the contents of the generated `objects/` folder into the `objects/` folder in your ExcellentCrates v7 installation, usually `plugins/ExcellentCrates/objects/`. Keep the subfolder structure.
5. Do not copy `manifest.json` or `conversion-report.json` into `objects/`. Read the report, restart the server, and check the crates in-game.

The output folder must be empty. The app will not overwrite existing files.

## Run from source

Requires Python 3.10 or later.

```powershell
py -m pip install -r requirements.txt
py src\gui.py
```

Command-line usage:

```powershell
py src\converter.py "C:\path\to\ExcellentCrates-v6.zip"
```

Map a legacy world name to a specific v7 world identifier:

```powershell
py src\converter.py "C:\path\to\ExcellentCrates-v6.zip" "excellentcrates [converted]" --world-map survival=minecraft:world1
```

GitHub Actions builds the standalone Windows executable. Pushing a `v*` tag creates a release with the executable attached.

## Converted data

- Crates, keys, ITEM and COMMAND rewards, previews, weights, effects, and supported cooldown settings.
- ITEM reward previews use the first item in the original `ItemsData` order.
- COMMAND rewards put legacy commands inside the v7 `commands.bundles` structure, with a stable bundle ID and a weight of `0.0`.
- Assigned blocks retain their coordinates and use world keys in the `minecraft:<world>` format.
- Referenced hologram templates from the legacy `config.yml` are copied into each crate; the vertical offset is increased by 0.7.
- Global and individual reward limits preserve their amounts.
- Crate milestones and their reward references.
- Legacy animation profiles are mapped to v7 profiles: legacy CSGO profiles use `csgo_animation:default`; other profiles use `simple_roll:default`.

`conversion-report.json` lists items that need manual review.

## Limitations

The converter does not migrate `data.db`, custom menus, languages, global settings, logs, currency costs, or some advanced permissions. Milestone structures and item NBT data may vary by ExcellentCrates, Minecraft, or installed extensions. Review the output in-game before using it on a live server.

## Contributing

Bug reports and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md), and anonymize configuration files before sharing them.

## License

Released under the [MIT License](LICENSE).
