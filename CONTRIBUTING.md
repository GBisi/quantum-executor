# Contributing Guide

Welcome 👋 and thank you for considering a contribution!

---

## ✨ Quick Start (90 seconds)

```bash
# 1. Fork and clone
git clone https://github.com/GBisi/quantum-executor
cd quantum-executor

# 2. Install Python 3.12 and Poetry (if not already)
#    https://python-poetry.org/docs/#installation

# 3. Set up the dev environment
poetry install --with dev

# 4. Activate the virtualenv and install git hooks
poetry shell
pre-commit install --hook-type pre-commit --hook-type commit-msg

# 5. Run the full test & lint suite (optional but recommended)
pre-commit run --all-files      # lint / type-check / docs
pytest -vv --cov                # unit tests
```

You’re now ready to hack on the project 🚀

---

## 🛠️ Local Development Workflow

1. **Create a feature branch**

   ```bash
   git checkout -b feat/your-awesome-idea
   ```

2. **Write code & tests**

   * Follow the *NumPy Docstring* standard for docstrings.
   * Keep functions typed.

3. **Run hooks before committing**

   ```bash
   pre-commit run             # checks staged files only
   git add .
   cz commit                  # interactive conventional commit (Commitizen)
   ```

4. **Run the full suite**

   ```bash
   pytest -vv --cov html:htmlcov tests/
   ```

5. **Push & open a PR**

   ```bash
   git push --set-upstream origin feat/your-awesome-idea
   ```

   Our CI (GitHub Actions) will automatically:
   * Re-run all *pre-commit* hooks on **Python 3.12**.
   * Run the full test matrix on Python.
   * Build the documentation (`docs/_build/html`).
   * Upload coverage to Codecov.

---

## 📐 Coding Standards

| Layer | Tool | Enforced Where |
|-------|------|----------------|
| **Formatting** | Ruff | pre-commit & CI |
| **Linting** | Ruff – staged rule-set (`pyproject.toml`) | pre-commit & CI |
| **Static typing** | MyPy (`pyproject.toml`) | pre-push & CI |
| **Security** | Ruff-S rules, Bandit, Gitleaks, Pip-audit | pre-commit & CI |
| **Tests** | PyTest, Coverage ≥ 90 % | local & CI |
| **Docs** | Sphinx (+ NumPy DocStyle) | pre-push & CI |

### Ruff Stages

If you’re unsure why Ruff complains, run:

```bash
ruff check <path> --show-source --select <RULE>
```

…and read the short explanation it prints.

---

## 📝 Commit Messages

We follow **Conventional Commits** and enforce them with **Commitizen**.

```
feat(query): add dispatcher to quantum executor
fix(scheduler): handle shot overflow edge case
docs: rewrite API usage section
```

Use `cz commit` for an interactive prompt – it won’t let you get it wrong.

---

## 📚 Documentation

```bash
# Build docs locally
sphinx-build -b html -W docs docs/_build/html
open docs/_build/html/index.html
```
---

## 🧪 Tests & Coverage

* Write **unit tests** alongside new features (`tests/`).
* Aim for **≥ 90 % line coverage**; CI enforces it.
* Use *pytest fixtures* for expensive QPU simulations to avoid long runtimes.

---

## 🔒 Security

* Never commit credentials or API tokens – `gitleaks` blocks them.
* Never disable security rules in Ruff/Bandit without a comment explaining why.

---

## 🏷️ Pull Request

Make PRs on the `dev` branch using **Squash & Merge** to keep a linear history.

---

## 🙋 Need Help?

* Open a **GitHub Discussion** for general questions.
* Open an **Issue** for bugs or feature requests (use the templates).
* Ping maintainers in the PR if CI fails and you’re stuck.

---

## 🤝 Code of Conduct

We adhere to the [Contributor Covenant](https://www.contributor-covenant.org/) & strive for a welcoming, inclusive environment.
Harassment, discrimination, or disrespectful behavior is **not tolerated**.

---

Happy hacking! We’re excited to see what you’ll create.

— *The Quantum Executor Maintainers*
