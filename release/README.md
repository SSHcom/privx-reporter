# Publishing Reporter Docker Images

Use `release/build.sh` to build Reporter images with Docker Buildx.
The script builds with `--sbom=true` to generate SBOM attestations.

## Usage

```bash
release/build.sh <component|all> [--dev] [--push] [--version <x.x.x>] [docker-build-args...]
```

Components: `cli`, `ui`, `sync`, `all`

## Flag behavior

- `--dev`
  - Uses `-dev` image names (for example `privxsshcom/privx-reporter-cli-dev:latest`).
- `--push`
  - Pushes images directly from Buildx (`docker buildx build --push`).
  - Without this flag, images are loaded locally (`docker buildx build --load`) and not pushed.
- `--version <x.x.x>`
  - Adds an additional version tag besides `:latest`.
- `docker-build-args...`
  - Passed through to `docker buildx build` (for example `--build-arg KEY=VALUE`).

## Examples

- Build all production images locally:
  - `release/build.sh all`
- Build and push all production images:
  - `docker login`
  - `release/build.sh all --push --version 1.0.0`
- Build and push dev CLI image with an extra version tag:
  - `docker login`
  - `release/build.sh cli --dev --push --version 1.2.3`

## Problem solving

### Docker is unable to copy a file or directory

- Check that `/.dockerignore` does not hide the resource