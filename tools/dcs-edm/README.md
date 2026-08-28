# DCS EDM Export Toolchain

Reusable, headless DCS model export pipeline.

## Pinned native toolchain

- Windows GitHub Actions runner
- Blender 4.1.1 portable
- Eagle Dynamics official Blender-EDM-Exporter
- Official exporter commit: `5f03ba70ec96ca6ce68028eabc786ecd97f9cf93`
- Native Windows `pyedm_311.pyd` is mandatory. The runner aborts if the dummy/non-native exporter is loaded.

The pinned ED commit is the initial public official exporter build. Its platform selector explicitly sends Blender 4.x on Windows through `pyedm_311`, including Blender 4.1.x.

## Job modes

Put a JSON job at `edm-jobs/job.json`.

### Build from Blender Python

```json
{
  "mode": "script",
  "script": "edm-jobs/build_model.py",
  "output": "My_DCS_Asset.edm",
  "save_blend": true
}
```

### Export an existing blend already in the repository

```json
{
  "mode": "blend",
  "blend": "edm-jobs/My_DCS_Asset.blend",
  "output": "My_DCS_Asset.edm",
  "save_blend": true
}
```

Either mode may include `post_script` for EDM-specific connector, animation, collision, or validation setup.

## Triggering

Any push changing the workflow, `tools/dcs-edm/**`, or `edm-jobs/**` runs the exporter automatically. It can also be launched manually with workflow dispatch.

## Output

Every successful run uploads an artifact containing the EDM, generated/export-ready blend when requested, and an `edm-build-report.json` with Blender version, native-binding status, exporter commit, file size, SHA-256, and exporter messages.

## Safety checks

The build fails rather than returning a fake EDM if Blender is not exactly 4.1.1, the runner is not Windows, official `io_scene_edm` cannot load, native `pyedm_311` is unavailable, the scene is empty, ED reports failure, or the EDM is missing/empty.

This is intentionally project-agnostic for future DCS ships, vehicles, launchers, statics, weapons, animated turrets, collision shells, and other EDM modeling tasks.
