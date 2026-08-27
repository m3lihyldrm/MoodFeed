# Contributing to MoodFeed

Thank you for your interest in contributing to MoodFeed!

---

## 1. Development Guidelines

1. Ensure all code conforms to Python 3.11+ type annotations.
2. Run test suite before committing:
   ```bash
   python -m compileall backend tests scripts
   python -m pytest -v
   git diff --check
   ```
3. Never hardcode secrets, tokens, or personal identifiers.
4. Keep the separation between client-side demo mode and server-side production APIs clear.
