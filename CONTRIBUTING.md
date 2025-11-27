# Development - Contributing

Issues and pull requests are more than welcome: https://github.com/cogeotiff/rio-tiler-pds/issues

We recommand using [`uv`](https://docs.astral.sh/uv) as project manager for development.

See https://docs.astral.sh/uv/getting-started/installation/ for installation

**dev install**

```bash
git clone https://github.com/cogeotiff/rio-tiler-pds.git
cd rio-tiler-pds

uv sync
```

You can then run the tests with the following command:

```sh
uv run pytest --cov rio_tiler_pds --cov-report term-missing
```

### pre-commit

This repo is set to use `pre-commit` to run *isort*, *flake8*, *pydocstring*, *black* ("uncompromising Python code formatter") and mypy when committing new code.

```bash
uv run pre-commit install
```

### Docs

Hot-reloading docs:

```sh
git clone https://github.com/cogeotiff/rio-tiler-pds
cd rio-tiler-pds
uv run --group docs mkdocs serve -f docs/mkdocs.yml
```

To manually deploy docs (note you should never need to do this because Github
Actions deploys automatically for new commits.):

```sh
uv run --group docs mkdocs gh-deploy -f docs/mkdocs.yml
```
