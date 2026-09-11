# Contributing to AEE

Thank you for considering a contribution. Here is how to start.

## Quick Start

```bash
git clone https://github.com/lErrorl404l/AEE.git
cd AEE
hemtt check -p -e
hemtt build
python3 -m unittest discover -s tools/tests
```

## Pull Request Process

1. Keep pull requests small and focused. One feature or fix per request.
   Discuss large changes in an issue first.
2. Run the gates before you push:
   ```bash
   hemtt check -p -e
   python3 -m unittest discover -s tools/tests
   ```
3. The repository uses `.githooks/`. Install them with:
   ```bash
   git config core.hooksPath .githooks
   ```
   The hooks run `hemtt check -p -e`, `ste-lint`, and the rules audit
   before every commit.
4. Sign your commits. The repository requires GPG-signed commits.
5. Headless verification: run `tools/docker_test.sh` if you changed
   simulation logic. All five mission phases must pass.

## Code Standards

### SQF

- One function per file: `functions/fnc_<name>.sqf`.
- Register each function in `XEH_PREP.hpp` with `PREP(<name>)`.
- Use the standard file header: params, return value, example. The
  `.vscode/sqf.code-snippets` file provides the header template.
- Private variables start with an underscore. No global namespace
  pollution; use `GVAR` / `QGVAR` / `EGVAR`.
- Parenthesise `&&` and `||` operands. Arma groups these operators
  tighter than `==` and `>`.
- On a dedicated server there is no player unit. Guard unit-dependent
  code with `if (isNull _unit) exitWith {}` and default to `objNull`.
- Call functions with `[] call FUNC(name)`. A bare `call FUNC(name)`
  inherits the caller's `_this`.
- Tab indentation, 4 spaces per tab.

### Config

- Every addon declares `CfgPatches` with `requiredAddons` and the
  `VERSION_CONFIG` macro.
- No `ace_common` dependency in the core addons. Keep the core standalone.
- Compat addons gate on their host with `skipWhenMissingDependencies`.

### Writing

- Use ASD-STE100 controlled English: British spelling, short sentences,
  active voice. No semicolons or em dashes.

## Versioning

Version numbers live in `addons/main/script_version.hpp`. Bump them at
release time. The pre-build hook writes the version into mod.cpp.

## Report a Vulnerability

Follow [SECURITY.md](SECURITY.md). Do not open a public issue for an
exploitable flaw.