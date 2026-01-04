# Contributing to JournalSmart

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Code of Conduct

Be respectful and constructive. We welcome contributors of all backgrounds and experience levels.

## How to Contribute

### Reporting Bugs

1. Check existing [issues](https://github.com/fbsobreira/JournalSmart/issues) to avoid duplicates
2. Create a new issue with:
   - Clear title describing the bug
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Python version, browser)

### Suggesting Features

1. Open an issue with the `enhancement` label
2. Describe the use case and proposed solution
3. Be open to discussion and alternatives

### Submitting Code

1. **Fork** the repository
2. **Create a branch** for your feature/fix:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make changes** following the code style below
4. **Test** your changes thoroughly
5. **Commit** with clear messages:
   ```bash
   git commit -m "feat: add new feature description"
   ```
6. **Push** to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```
7. **Open a Pull Request** against `main`

## Code Style

### Python

- Follow PEP 8
- Use type hints where practical
- Run linting before committing:
  ```bash
  make lint
  ```

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation only
- `style:` - Formatting, no code change
- `refactor:` - Code change without feature/fix
- `test:` - Adding tests
- `chore:` - Maintenance tasks

### JavaScript

- Use modern ES6+ syntax
- Prefer `const` over `let`
- Use meaningful variable names

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/JournalSmart.git
cd JournalSmart

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment config
cp .env.example .env
# Edit .env with your QuickBooks sandbox credentials

# Run the app
python run.py
```

## Testing

Currently, the project does not have automated tests. Contributions to add testing infrastructure are especially welcome!

When testing manually:
1. Test with QuickBooks sandbox environment first
2. Verify CSRF protection works (forms should fail without tokens)
3. Check that OAuth flow completes successfully
4. Verify mappings CRUD operations work correctly

## Pull Request Guidelines

- Keep PRs focused on a single change
- Update documentation if needed
- Ensure no secrets or credentials are committed
- Test with both sandbox and production environments if possible
- Be responsive to feedback and requested changes

## Security Issues

**Do not open public issues for security vulnerabilities.**

Please report security issues privately. See [SECURITY.md](SECURITY.md) for instructions.

## Questions?

Open an issue with the `question` label or start a discussion.

## License

By contributing, you agree that your contributions will be licensed under the AGPL-3.0 license.

