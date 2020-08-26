# Development - Contributing

Issues and pull requests are more than welcome: https://github.com/cogeotiff/rio-tiler-pds/issues

**dev install**

```bash
$ git clone https://github.com/cogeotiff/rio-tiler-pds.git
$ cd rio-tiler-pds
$ pip install -e .[dev]
```

**Python3.7 only**

This repo is set to use `pre-commit` to run *isort*, *flake8*, *pydocstring*, *black* ("uncompromising Python code formatter") and mypy when committing new code.

```bash
$ pre-commit install
```

### Docs

```
pip install rio_tiler_pds[docs]
```

Hot-reloading docs:

```
git clone https://github.com/cogeotiff/rio-tiler-pds
cd rio-tiler-pds
mkdocs serve
```

To manually deploy docs (note you should never need to do this because Github
Actions deploys automatically for new commits.):

```
mkdocs gh-deploy
```
