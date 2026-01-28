# Testing Guide

## Running Tests Locally

```bash
# Run all tests
python test.py

# Run with more detail
python test.py -v
```

## What We Test

### 1. URL Rewriting ✅
- Relative URLs get `/service/` prefix
- Absolute URLs stay untouched
- Already-prefixed URLs don't get double-prefixed
- Base tags, fetch calls, location.href all handled

### 2. Edge Cases ✅
- Empty content doesn't crash
- Malformed HTML handled gracefully
- Special characters in service names work

### 3. Regression Prevention 🛡️
- MathJax scripts get prefixed (was broken before)
- Data URLs not modified
- Protocol-relative URLs (`//cdn.com`) preserved

## Before Submitting a PR

1. **Run the tests:**
   ```bash
   python test.py
   ```

2. **Test manually with DEBUG mode:**
   ```bash
   DEBUG=true python wsgi.py
   # Visit http://localhost:8080/yourservice/
   ```

3. **Check the logs:**
   - Look for `[REWRITE]` messages
   - Verify URLs are being modified correctly
   - No unexpected errors

## Adding New Tests

Keep it **light and focused**. Test core functionality, not every edge case.

**Good test:**
```python
def test_my_feature(self):
    """Clear description of what we're testing."""
    html = '<simple example>'
    result = rewrite_content(html, 'service', 'example.com')
    self.assertIn('expected output', result)
```

**Bad test:**
```python
def test_everything_possible(self):
    # 100 lines of complex setup...
    # Testing implementation details...
    # Fragile assertions...
```

## CI/CD

Tests run automatically on:
- Every push to `main`
- Every pull request

PRs must pass tests before merging.

## Common Issues

**Tests fail locally but work in CI?**
- Check Python version (we use 3.11)
- Make sure dependencies are installed

**Rewriting not working as expected?**
- Check `views.py` `rewrite_content()` function
- Add a test case for your scenario
- Verify with DEBUG=true logs

---

**Keep it simple. Keep it working.** 🚀