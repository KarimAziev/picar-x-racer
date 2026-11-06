# Repository Guidelines

## Project Structure & Module Organization
`backend/app/` contains the Python backend: `api/` endpoints, `services/` domain logic, `adapters/` hardware integrations, `schemas/` data models, and `core/` utilities. Entry points live in `backend/run.py`, `backend/run_main_app.py`, and `backend/run_car_control_app.py`. `backend/tests/` mirrors backend domains such as `services/`, `managers/`, `core/`, and `util/`. `frontend/src/` is organized by feature, with shared code under `ui/`, `views/`, `router/`, `api/`, and `assets/`. Runtime assets and examples live in `data/`, `demo/`, `music/`, and `sounds/`.

## Working Practices For Agents
Read the surrounding implementation before editing. This project already has useful boundaries, so prefer extending existing schemas, services, stores, and composables over adding parallel mechanisms. Use `rg` for navigation and check all call sites before changing a shared type or endpoint payload.

The worktree may contain local or staged user changes. Do not reset, checkout, or overwrite unrelated files. If a file is already dirty, inspect the diff first and patch around the existing edits. Mention unrelated dirty files in the handoff when relevant.

## Build, Test, and Development Commands
- `make all`: install frontend dependencies, build the UI, and provision the backend virtual environment.
- `make dev`: start the main API, control server, and Vite dev server with reload support.
- `make backend-run`: run the backend stack from `backend/.venv`.
- `make test`: run both backend and frontend test suites.
- `make check`: run Pyright, Black, backend and frontend tests, Vue type checking, and the frontend production build.
- `make format-backend`: format backend Python files with Black.
- `cd frontend && npm run build`: create the production frontend bundle.
- `cd backend && . .venv/bin/activate && pyright && black --check .`: run the backend checks used in CI.
- `cd backend && . .venv/bin/activate && python -m unittest discover`: run the full backend suite.
- `cd frontend && npm test`: run the Vitest suite.
- `git diff --check`: check for whitespace errors before handing off edits.

## Coding Style & Naming Conventions
Python uses 4-space indentation, `snake_case` module names, and Black formatting. Keep backend names aligned with their role and folder, for example `camera_service.py` or `settings.py`. Vue and TypeScript use 2-space indentation, double quotes, `PascalCase` for components such as `SettingsPopup.vue`, and `camelCase` for composables and utilities such as `useKeyboardControls.ts`. Keep new frontend work under `frontend/src/features/<domain>/` when it is feature-specific.

## Testing Guidelines
Backend tests use `unittest`; add files as `backend/tests/**/test_*.py` and mirror the production module they cover. Frontend tests use Vitest with `*.test.ts`, usually close to the code under test. Run `make check` before opening a PR. For backend-heavy work, also run `cd backend && . .venv/bin/activate && coverage run --source=app -m unittest discover`. No numeric coverage threshold is configured, but new behavior should include regression tests.

When touching shared filtering, queue payloads, detection settings, or camera media paths, add focused regression tests first and then run the broader suite. `pyright` is intentionally strict; fix type issues in tests too instead of masking them with broad casts.

## Detection And Camera Flow
Detection settings are defined in `backend/app/schemas/detection.py` and mirrored in the front end under `frontend/src/features/detection/`. Runtime settings are pushed through `DetectionService` into `backend/app/managers/detection/detection_process.py` via `DetectionControlMessage`; only model/image-size style process-bound changes should restart the detection process.

The core inference parser is `backend/app/managers/detection/object_detection.py`. Preserve the distinction between result types:
- Object, pose, and instance segmentation models produce `detection_result` entries with `bbox`, `label`, `confidence`, and optional `keypoints` or `segments`.
- Semantic segmentation models produce a full-frame class map as `semantic_mask`; do not force semantic output into fake boxes.
- Instance segmentation polygons should be mapped back from letterboxed model coordinates into original frame coordinates.
- Semantic masks should be cropped out of letterbox padding, resized with nearest-neighbor interpolation, and sent compactly.

Live detection overlays are drawn on the front end through `frontend/src/ui/ImageFeed.vue` and `frontend/src/features/detection/overlays/`. Captured photos and recorded videos use backend-side drawing through `backend/app/util/photo.py` and `backend/app/util/overlay_detecton.py`. When adding or changing an overlay style, update both paths unless the feature is explicitly live-only.

Camera lifetime and stream behavior spans `backend/app/services/camera/camera_service.py`, `stream_service.py`, and the websocket endpoints. Be careful with thread/process cleanup and queue draining; prefer existing `clear_and_put`, `poll_detection_result`, and service lifecycle helpers.

## File Listing And Model Selection
File APIs are in `backend/app/api/endpoints/file_management.py`; generic listing behavior lives in `backend/app/managers/file_management/file_manager.py` and `backend/app/services/file_management/file_filter_service.py`. Detection model listing is specialized in `backend/app/services/detection/detection_file_service.py`, where local model files and synthetic `loadable` model entries are combined.

When changing `/api/files/list/data`, ensure local files and loadable model suggestions pass through the same search, filter, ordering, and grouping logic. Empty date filters should behave as no-ops, especially because loadable model entries have `modified = None`.

The model selector UI is `frontend/src/features/detection/components/ModelSelect.vue`. The reusable tree component exposes slots; prefer local slots for detection-specific row badges or labels instead of changing `frontend/src/ui/TreeSelect.vue` for a one-off model-selection need.

## Frontend Notes
Pinia stores are the source of truth for feature state. For detection, keep `DetectionSettings`, websocket response types, defaults, settings fields, and UI controls synchronized. `frontend/src/features/settings/config.ts` derives select options from enums, so adding a new enum value often updates the UI automatically, but field defaults and form state still need explicit updates.

Canvas overlays should avoid per-frame layout churn. Keep canvas dimensions stable unless the displayed image size changes, coalesce redraws with `requestAnimationFrame`, and prefer bitmap drawing for dense masks over thousands of individual path operations.

## Commit & Pull Request Guidelines
Recent history follows Conventional Commit prefixes such as `feat:`, `fix:`, `refactor:`, and `style:`. Keep commit subjects short, imperative, and specific, for example `fix: initialize GStreamer with empty args list`. PRs should summarize the behavior change, note hardware impact, list validation steps, and link the relevant issue when one exists. Include screenshots or GIFs for UI, streaming, or camera workflow changes.

## JSON Schema Migrations
Robot hardware configuration uses ordered, versioned JSON migrations. The reusable migration engine is in `backend/app/migrations/json_data.py`; robot-specific migrations and their registry live under `backend/app/migrations/robot_config/`. `JsonDataManager` runs the configured migrator before caching or writing data, validates the fully migrated document, and atomically persists successful upgrades of an existing target file. Do not bypass this path with ad hoc compatibility logic in Pydantic models or services, and do not modify a migration after it has been released.

For every hardware schema change that makes an existing `config.json` invalid, add the next `backend/app/migrations/robot_config/v<N>_<description>.py` migration, register it under target version `N` in `robot_config/__init__.py`, update `HardwareConfig.schema_version` to `Literal[N]`, and set the same `schema_version` in the default root `config.json`. Migrations must preserve unrelated fields, reject ambiguous input rather than guessing, and return a JSON object that validates as the current `HardwareConfig`. Add regression coverage under `backend/tests/migrations/` for direct transformation, version sequencing and errors, atomic target persistence, invalid-output rollback, and fallback-template behavior. Ensure nested test directories contain `__init__.py` so `python -m unittest discover` includes them.

## Configuration Tips
Copy `backend/.env.example` to `backend/.env` for local overrides. Do not commit secrets, generated files under `data/`, or build output from `frontend/dist/`.
