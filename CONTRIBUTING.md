# Contributing to Haven

Thanks for your interest in Haven — a context-aware household agent built
for Alexa+. This document covers how to get set up locally and how to
propose changes.

## Getting Started

1. Clone the repository.
2. Install dependencies with `pip install -e ".[dev]"` from the repo root.
3. Copy `.env.example` to `.env` and fill in any local values you need.
4. Run the household simulator with `python scripts/run_simulator.py` to
   confirm your environment is working.
5. Run the test suite with `pytest`.

## Project Structure

- `src/haven/models/` — Household domain models (people, rooms, devices)
  and the shared planning contracts.
- `src/haven/context/` — The Context Resolver: gathers only the facts
  needed for the current goal, from approved sources.
- `src/haven/agents/`, `src/haven/planning/` — Planning and reasoning.
- `src/haven/execution/`, `src/haven/verification/` — Deterministic
  execution of a plan and verification of its results.
- `src/haven/mcp/` — The MCP server and tools exposed to Alexa+.
- `simulator/` — Local simulators for the household, media, and security
  services, so Haven can be developed and demoed without real hardware.
- `aws/` — AWS integrations (Bedrock, DynamoDB, AgentCore, IAM).
- `apps/` — The Alexa+ project configuration and the Haven dashboard.

## Code Style

- Follow the existing style in the module you're editing: a short header
  comment describing the module's purpose, `# comment`-style explanations
  above logic rather than long inline prose, and type hints throughout.
- Keep planning/reasoning code and deterministic logic clearly separated.
  Constraints that can be checked deterministically (available time,
  device state) should never be left to an LLM to reason about.
- Every public function or class should have a clear, single
  responsibility, matching the interface it was designed against.

## Making Changes

1. Open an issue or check existing ones before starting significant work.
2. Create a branch from `main`.
3. Keep changes scoped — small, reviewable pull requests are easier to
   merge quickly during the hackathon window.
4. Add or update tests for any behavior you change.
5. Update relevant documentation in `docs/` if your change affects it.
6. Open a pull request describing what changed and why.

## Reporting Issues

When filing an issue, please include:

- What you expected to happen.
- What actually happened.
- Steps to reproduce, including any relevant simulator or MCP request
  payloads.

## Friction Log

If something about Haven's tools, SDKs, or development process was
confusing, slow, or broken, please add an entry to
`docs/friction-log.md` as you go rather than waiting until the end.

## Code of Conduct

Be respectful and constructive. This project is built in a short,
high-intensity window, so clear and kind communication matters.
