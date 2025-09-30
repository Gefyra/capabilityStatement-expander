# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Smart example detection via meta.profile references
- Enhanced documentation with detailed feature descriptions
- Complete GitHub Action integration

### Changed
- Improved resource collection algorithm
- Enhanced logging and error handling

### Fixed
- Various bug fixes and stability improvements

## How to Release

To create a new release:

1. Update the version in this CHANGELOG.md
2. Commit your changes
3. Create and push a new tag:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
4. The GitHub Action will automatically create the release

## Version Format

- Use semantic versioning: `vMAJOR.MINOR.PATCH`
- Examples: `v1.0.0`, `v1.2.3`, `v2.0.0`
- Major version tags (e.g., `v1`, `v2`) are automatically updated