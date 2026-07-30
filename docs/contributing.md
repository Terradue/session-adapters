# Contributing

Clone the repository and create a Python environment supported by the project
(Python 3.10 through 3.14).

## Run the tests

```bash
hatch run test:test-q
```

## Run quality checks

```bash
hatch run dev:check
ruff format --check .
```

## Preview the documentation

```bash
hatch run docs:serve
```

Open `http://127.0.0.1:8000/`. MkDocs reloads the site as documentation files
change.

Build the same strict documentation output used for validation:

```bash
hatch run docs:build
```

## Documentation structure

Place new content according to the reader's need:

- `tutorials/` teaches through a guided learning experience;
- `how-to/` helps an experienced reader complete a specific task;
- `reference/` states exact interfaces and behavior;
- `explanation/` develops concepts, rationale, and trade-offs.

Keep each page primarily in one category. Link to another category instead of
interrupting a procedure with extensive background or turning reference
material into a tutorial.

Examples must reflect tested behavior. When the implementation has a material
constraint, update `reference/limitations.md` and link to it from the affected
guide.
