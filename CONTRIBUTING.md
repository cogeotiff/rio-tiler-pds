# Development - Contributing

Issues and pull requests are more than welcome: https://github.com/cogeotiff/rio-tiler-pds/issues

**dev install**

```bash
$ git clone https://github.com/cogeotiff/rio-tiler-pds.git
$ cd rio-tiler-pds
$ pip install -e .["test,dev"]
```

You can then run the tests with the following command:

```sh
python -m pytest --cov rio_tiler_pds --cov-report term-missing
```

### pre-commit

This repo is set to use `pre-commit` to run *isort*, *flake8*, *pydocstring*, *black* ("uncompromising Python code formatter") and mypy when committing new code.

```bash
$ pre-commit install
```

### Docs

```sh
pip install rio_tiler_pds["docs"]
```

Hot-reloading docs:

```sh
git clone https://github.com/cogeotiff/rio-tiler-pds
cd rio-tiler-pds
mkdocs serve -f docs/mkdocs.yml
```

To manually deploy docs (note you should never need to do this because Github
Actions deploys automatically for new commits.):

```sh
mkdocs gh-deploy -f docs/mkdocs.yml
```
