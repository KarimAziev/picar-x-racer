# Frontend Guidelines

Read and follow [../AGENTS.md](../AGENTS.md) for repository-wide guidance. This
file applies to `frontend/` and its descendants. Paths below are relative to
`frontend/` unless stated otherwise. The backend is available at `../backend/`.

## Project Structure

The frontend uses Vue 3, TypeScript, Pinia, Vue Router, PrimeVue, Tailwind CSS,
and Vite.

- `src/features/<domain>/`: feature components, stores, types, and composables.
- `src/ui/`: reusable UI components.
- `src/composables/`: shared Vue composables.
- `src/util/`: shared guards and utility functions.
- `src/api/`: shared API code.
- `src/views/` and `src/router/`: views and routing.
- `src/assets/`, `src/config/theme.ts`, and `src/presets/`: styles, theme
  configuration, and component presets.

Read surrounding implementations and check call sites before changing shared
components, types, or payloads. Extend existing stores, composables, and utilities
instead of introducing parallel mechanisms. Preserve unrelated worktree changes;
inspect existing diffs before editing dirty files.

## Development and Validation

Run these commands from `frontend/`:

- `npm run dev`: start the Vite development server.
- `npm test`: run the Vitest suite once.
- `npm test -- src/path/example.test.ts`: run a focused test file.
- `npm run type-check`: run Vue and TypeScript type checking.
- `npm run build`: type-check and build the production bundle.
- `npm run preview`: preview the production bundle.
- `git diff --check`: check whitespace before handing off edits.

From the repository root, use `make dev` to start the backend and frontend
together, and run `make check` before opening a PR. Do not commit generated
`dist/` output or secrets.

Keep Vitest tests close to the code they cover, using `*.test.ts`. Add regression
coverage for new behavior. For shared filtering, queue payloads, detection
settings, or camera media paths, add focused regression tests first, then run the
broader suite. Validate UI changes at mobile and desktop sizes and include
screenshots or GIFs in UI, streaming, or camera workflow PRs.

## Code Style

Use 2-space indentation, double quotes, `PascalCase` component filenames, and
`camelCase` utilities and composables. Use `<script setup lang="ts">` for Vue
components.

### Use functional transforms over imperative loops

Prefer `map`, `filter`, `flatMap`, and `reduce` for data transformations. This
reduces the mutation surface and makes intent clearer. Keep accumulator mutation
local to the transform.

Avoid:

```ts
const input = { a: 1, b: 2 };
const out: Record<string, number> = {};

for (const [key, value] of Object.entries(input)) {
  out[key] = value * 10;
}
```

Prefer:

```ts
const input = { a: 1, b: 2 };

const out = Object.entries(input).reduce<Record<string, number>>(
  (acc, [key, value]) => {
    acc[key] = value * 10;
    return acc;
  },
  {},
);
```

### Prefer explicit, strict typing

Always use strict types. Prefer concrete domain types, discriminated unions, and
generics; avoid `any`, `unknown`, and `Record<string, unknown>` when possible.
Type component props, emitted events, store state, and API payloads. Narrow
untrusted values with guards before use, and do not silence type errors with
broad casts.

### Use strict equality and shared guards

Never use `==` or `!=`; use `===` and `!==` for equality comparisons. For guards,
including type checks and checks for empty strings, `null`, or `undefined`, always
use predicates from `src/util/guards.ts`, imported through `"@/util/guards"`.

Available helpers include `isPlainObject`, `isError`, `isEmptyString`, `isEmpty`,
`isString`, `isNumber`, `isBoolean`, `isArray`, `isNull`, `isUndefined`, `isNil`,
`anyPass`, and `allPass`. Reuse and compose these predicates instead of writing
inline `typeof` checks or duplicating guard logic.

### Reuse utilities and use alias imports

Check `src/util/` before implementing common operations. Shared helpers include
`arr.ts`, `str.ts`, `dom.ts`, `ts-helpers.ts`, `obj.ts`, `error.ts`, and `func.ts`.

Always use the `@/` path alias for imports within `src/`, including imports from
the same directory. For example, use `"@/util/guards"` and `"@/ui/Field.vue"`.
External packages retain their package import names.

## Vue Components and Styling

- Split components into focused, reusable parts. Keep feature-specific parts
  under their feature directory and shared components under `src/ui/`.
- Make components extensible through slots. Prefer feature-local slots for
  specialized row content over adding domain-specific behavior to shared UI.
- Keep Pinia stores as the source of truth for feature state and reuse existing
  composables for shared behavior.
- Prefer Tailwind utility classes over SCSS.
- Use theme colors and semantic tokens instead of hardcoded color values. Rare
  semantic exceptions, such as red for errors, are acceptable.
- Use adaptive layouts that support mobile screens, touch input, and desktop
  interaction. Ensure controls and content remain usable at narrow widths.

## Backend Contracts and Canvas Overlays

Keep frontend settings, websocket response types, defaults, and UI controls
synchronized with schemas in `../backend/`. Detection select options derive from
enums in `src/features/settings/config.ts`; defaults and form state still require
explicit attention when adding values.

Live overlays use `src/ui/ImageFeed.vue` and `src/features/detection/overlays/`.
Keep canvas dimensions stable unless the displayed image size changes, coalesce
redraws with `requestAnimationFrame`, and use bitmap drawing for dense masks.
Preserve the distinction between instance detections and full-frame semantic
masks. Overlay style changes must also cover backend photo and video rendering
unless the feature is explicitly live-only; see `../AGENTS.md` for those paths.

## Documentation and Comments

Write for readers who have not seen the conversation or a previous version.
Describe current behavior and constraints. Do not narrate edits, mention removed
or renamed implementation details, or justify decisions through conversation
history. Keep relevant history in changelogs, migration guides, deprecation
notices, or comments explaining non-obvious constraints. Report changes in chat.
