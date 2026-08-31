# New Room

New Room is a standalone product for transparent multi-agent collaboration.

## Project boundary

- New Room is not part of DeepSeek Harness.
- The recovered Tokenwerk DSH tree is template and implementation-history evidence, not the project identity or deployment target.
- Synthetic Sociality and Synthetic Sociality Room are separate projects.
- No external publication or deployment follows from this repository without separate authorization.

## Current release stage

K13 recovers the completed Room implementation into this durable repository, records path-level provenance, and freezes an immutable local candidate for independent review. See [the project charter](docs/PROJECT-CHARTER.md), [recovery provenance](docs/K13-RECOVERY-PROVENANCE.md), [verification results](docs/K13-GATE-RESULTS.md), and [template dependencies](docs/K13-TEMPLATE-DEPENDENCIES.md).

## Development

The recovered implementation currently retains the Tokenwerk DSH plugin substrate. Install the pinned workspace dependencies and use the repository commands documented in [AGENTS.md](AGENTS.md). The K13 production build is:

```sh
corepack pnpm run build
```

## License

[MIT](LICENSE)

Third-party dependencies and their licenses are disclosed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
