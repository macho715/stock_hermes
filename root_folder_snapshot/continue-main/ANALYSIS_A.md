# ANALYSIS_A.md — Continue Monorepo Reconnaissance Report

## Project Type and Purpose

Continue is an **open-source AI coding assistant IDE plugin** (VS Code + JetBrains extensions + CLI) that runs configurable LLM-powered agents as GitHub status checks on pull requests. It uses a YAML-defined check system (`.continue/checks/`) where each check is a markdown file describing a review task (security, test coverage, best practices, etc.). The core product is the extension that provides autocomplete, inline edit suggestions, chat interface, and code review automation directly inside the IDE.

## Core Entry Points

| File | Role |
|------|------|
| `core/core.ts` | Main library entry point for core AI logic |
| `extensions/vscode/src/extension.ts` | VS Code extension activation entry point |
| `extensions/cli/src/index.ts` | CLI entry point (`cn` command) |
| `core/config/ConfigHandler.ts` | Configuration loading and profile management |
| `gui/` | React-based GUI frontend |

## Technology Stack

- **Language**: TypeScript throughout (with JSX for GUI)
- **Runtime**: Node.js (`.nvmrc`, `.node-version`)
- **Monorepo tooling**: Likely npm workspaces or pnpm
- **Linting/Formatting**: ESLint, Prettier, TypeScript compiler
- **Testing**: Vitest (unit), Playwright (E2E)
- **Package manager**: npm (package-lock.json present)
- **Key dependency**: `@ai-sdk/deepseek` in root (indicates multi-provider LLM support)

## Module Structure (key src/ directories)

```
continue-main/
├── core/                    # Shared library — autocomplete, config, indexing, protocol
│   ├── autocomplete/        # Code completion engine (context, filtering, generation, templating)
│   ├── config/              # ConfigHandler, profiles, slash commands
│   ├── indexing/             # Code indexing and retrieval
│   ├── diff/                # PR diff analysis
│   ├── nextEdit/            # Next-edit suggestion logic
│   ├── protocol/            # Message protocol types
│   └── rules.md             # Core rule definitions
├── extensions/
│   ├── vscode/               # VS Code extension (activation, autocomplete, diff, quick-edit, lang-server)
│   ├── intellij/             # JetBrains extension
│   └── cli/                  # CLI tool (`cn`) — commands, permissions, TUI
├── gui/                      # React frontend for chat/GUI
├── binary/                   # Native IPC binary (TCP/IPC messenger)
├── packages/
│   └── config-yaml/          # Config YAML schema/parser package
├── .continue/
│   ├── agents/               # Agent definitions (security-review, test-coverage, etc.)
│   ├── checks/               # YAML check definitions (anti-slop, react-best-practices, etc.)
│   ├── prompts/              # Prompt templates for sub-agents
│   └── rules/                # Coding-style rules (TypeScript, CSS, documentation standards)
└── docs/                     # Documentation
```

## Existing README Sections Found

- README.md: Banner, "Getting started", "How it works", example YAML check, CLI install instructions (macOS/Linux/Windows)
- extensions/vscode/README.md
- extensions/vscode/CONTRIBUTING.md
- extensions/intellij/README.md, CONTRIBUTING.md
- extensions/cli/README.md, BUILD.md, AGENTS.md, CHANGELOG.md
- gui/README.md
- docs/README.md
- core/indexing/README.md, core/diff/test-examples/README.md, core/vendor/README.md
- core/nextEdit/README.md, core/rules.md
- actions/README.md, binary/README.md
- packages/config-yaml/src/README.md, CHANGELOG.md

## Relevance to Stock Trading System

**Not relevant.** This is the Continue VS Code extension monorepo — an AI coding assistant plugin. The `stock-pred-v5` project in `stock-pred-v5/` is a stock-candidate recommendation engine. They are completely separate codebases. This analysis confirms the project is a Node/TypeScript monorepo for an IDE plugin, not anything related to finance, trading, or quantitative analysis.