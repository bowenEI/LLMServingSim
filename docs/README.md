# Website

This website is built using [Docusaurus](https://docusaurus.io/), a modern static website generator.

## Installation

```bash
pnpm install
```

## Local Development

```bash
pnpm start
```

This command starts a local development server and opens up a browser window. Most changes are reflected live without having to restart the server. English documentation is available under `/en`; Chinese documentation is available under `/zh`.

## Build

```bash
pnpm build
```

This command first verifies that `docs/en/` and `docs/zh/` contain exactly the same relative file paths, then builds both trees into the same `build` directory. English pages are emitted under `build/en/`, and Chinese pages under `build/zh/`; the artifact can be served by any static content host.

## Deployment

Deployment is handled by GitHub Actions in `.github/workflows/deploy-docs.yml`. English sources live in `docs/en/` and Chinese sources in `docs/zh/`; changes to either tree rebuild the single Pages artifact, so both languages are deployed together. The custom domain is configured in `static/CNAME`.
