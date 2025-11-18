# Contributing to bw-patcher

Thank you for your interest in contributing! This project exists to help device owners understand and repair their hardware through transparent documentation of firmware systems.

## Before Contributing

**Please read and agree to:**
- [PRINCIPLES.md](PRINCIPLES.md) - Our core values
- [LEGAL_DISCLAIMER.md](LEGAL_DISCLAIMER.md) - Legal responsibilities
- This project's [CC-BY-NC-SA-4.0 License](LICENSE)

## Our Values

All contributions must align with our principles:
- ✅ Educational and research focus
- ✅ Prioritizing user safety
- ✅ Respecting the law
- ❌ No commercial exploitation
- ❌ No bypassing safety features for profit
- ❌ No encouraging illegal use

## How to Contribute

### Reporting Issues

**Security Vulnerabilities:**
If you discover a security vulnerability in manufacturer firmware:
1. DO NOT open a public issue
2. Contact the manufacturer directly for responsible disclosure
3. Wait for a reasonable time before public discussion

**Bugs and Feature Requests:**
Open a GitHub issue with:
- Clear description of the problem
- Steps to reproduce (if applicable)
- Expected vs. actual behavior
- Your environment (OS, Python version)

### Code Contributions

**We welcome:**
- Bug fixes
- Support for new device models
- Documentation improvements
- Test coverage improvements
- GUI/UX enhancements
- Error handling improvements

**We do NOT accept:**
- Code that explicitly bypasses safety features without clear warnings
- Removal of safety warnings or disclaimers
- Features designed primarily for commercial exploitation
- Code that violates manufacturer security without disclosure

### Pull Request Process

1. **Fork the repository** and create a feature branch
2. **Follow existing code style** (PEP 8 for Python)
3. **Add tests** for new functionality
4. **Update documentation** (README.md if user-facing changes)
5. **Run the test suite** if available
6. **Include disclaimer headers** in new files (see below)
7. **Sign your commits** to acknowledge the license
8. **Submit PR** with clear description of changes

### Commit Messages

Use clear, descriptive commit messages:
```
Good: "fix(mi5): Handle checksum calculation for patched firmware"
Good: "docs: Add safety warnings to README"
Bad: "fixed stuff"
Bad: "update"
```

### Code Style

- Follow PEP 8 Python style guide
- Use type hints where beneficial
- Keep functions focused and testable
- Add docstrings for complex functions
- Use meaningful variable names

### File Headers

All new Python files must include the license header:

```python
#!/usr/bin/env python3
#! -*- coding: utf-8 -*-
#
# BW Patcher
# Copyright (C) 2024-2025 ScooterTeam
#
# This work is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License.
# To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/
```

## Adding Support for New Models

If you've analyzed a new device model:

1. **Verify it's not already supported**
2. **Create a new module** in `bwpatcher/modules/`
3. **Implement required patching methods**
4. **Add comprehensive documentation** about the model
5. **Include safety considerations** specific to the model
6. **Test thoroughly** with multiple firmware versions

## Testing

Before submitting:
```bash
# Run tests if available
poetry run pytest tests/ -v

# Test CLI functionality
poetry run python -m bwpatcher model input.bin output.bin patches

# Test GUI
poetry run streamlit run app.py
```

## Documentation

Update documentation when changing:
- **README.md** - User-facing features, installation, usage
- **Docstrings** - Complex functions and classes

## Community Guidelines

### Be Respectful
- Treat all contributors with respect
- Provide constructive feedback
- Assume good intentions
- Welcome newcomers

### Stay On Topic
- Keep discussions focused on the project
- Use GitHub Issues for bug reports
- Don't spam or advertise

### No Illegal Activity
- Don't share stolen firmware
- Don't discuss bypassing laws
- Don't encourage dangerous modifications
- Don't facilitate commercial exploitation

## What Happens to Your Contribution

By contributing, you agree that:
- Your contribution will be licensed under CC-BY-NC-SA-4.0
- Your contribution may be modified by maintainers
- You have the right to contribute (no employer restrictions)
- You're not contributing proprietary/confidential information

## Questions?

- Open a GitHub Discussion for general questions
- Check existing Issues and Pull Requests first

## Recognition

Contributors will be acknowledged in:
- Git commit history
- Release notes (for significant contributions)

Thank you for helping make firmware more transparent and accessible! 🔓
