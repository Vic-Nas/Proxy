# Changelog

## Latest Release

### Added
- 🎯 Path-based reverse proxy (route multiple services via `/service/path`)
- 🔄 Smart URL rewriting (transparent to JavaScript apps)
- 📋 Logs service (`LOGS=true` → `/_logs/` endpoint)
- 🧪 Lightweight test suite with CI/CD
- 🎨 Beautiful error pages with optional coffee button
- 🐛 DEBUG mode with aggressive cache busting
- ✅ Duplicate service detection
- 📝 Complete documentation

### Features
- Service mapping via environment variables
- Pathname rewriting for JavaScript transparency
- Base tag, fetch(), location.href support
- Asset 404 pass-through (prevents MIME errors)
- Path vs service 404 distinction
- GitHub Actions auto-testing
- Auto-versioning and releases

### Configuration
- `SERVICE_*` - Define services
- `LOGS` - Enable logs viewer
- `DEBUG` - Verbose logging, no caching
- `FIXES` - Show this changelog on homepage
- `COFFEE` - Show/hide coffee button
- `COFFEE_USERNAME` - Customize support link

---

**Live demo:** https://vicnas.me