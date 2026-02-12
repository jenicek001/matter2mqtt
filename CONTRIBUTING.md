# Contributing to matter2mqtt

Thank you for your interest in contributing to the Matter-to-MQTT Bridge project! 🎉

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Style Guidelines](#style-guidelines)
- [Commit Messages](#commit-messages)
- [Pull Request Process](#pull-request-process)

## Code of Conduct

This project follows the standard open-source code of conduct:
- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive feedback
- Prioritize the community's best interests

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When creating a bug report, include:

- Detailed steps to reproduce
- Expected vs. actual behavior
- Environment information (hardware, OS, Docker version)
- Relevant logs from Docker containers
- MQTT topic outputs

Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.md).

### Suggesting Features

Feature requests are welcome! Please:

- Use the [feature request template](.github/ISSUE_TEMPLATE/feature_request.md)
- Clearly describe the use case and benefits
- Consider backward compatibility
- Think about how it fits with the project's goals

### Code Contributions

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Make your changes**
4. **Test thoroughly** on actual hardware if possible
5. **Commit your changes** (see commit message guidelines below)
6. **Push to your fork** (`git push origin feature/amazing-feature`)
7. **Open a Pull Request**

## Development Setup

### Prerequisites

- Raspberry Pi (3B+, 4, or 5)
- Docker and Docker Compose
- Thread radio (SkyConnect or compatible)
- Matter devices for testing (optional but recommended)

### Local Development

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/matter2mqtt.git
cd matter2mqtt

# Configure IPv6 (required!)
sudo ./scripts/setup-ipv6.sh

# Create .env file
cp config/.env.example .env

# Edit device paths in docker-compose.yml if needed
nano docker-compose.yml

# Build and start services
docker compose build
docker compose up -d

# View logs
docker compose logs -f matter-mqtt-bridge
```

### Testing Your Changes

Before submitting a PR, verify:

```bash
# All services start successfully
docker compose ps

# OTBR is operational
docker exec otbr ot-ctl state

# IPv6 is configured
sysctl net.ipv6.conf.all.forwarding

# MQTT bridge is publishing
mosquitto_sub -t 'matter/#' -v

# Bridge logs are clean
docker compose logs matter-mqtt-bridge | grep ERROR
```

## Style Guidelines

### Python Code

- Follow PEP 8 style guide
- Use meaningful variable names
- Add docstrings to functions and classes
- Keep functions focused and modular
- Use type hints where helpful

```python
def process_sensor_data(node_id: int, data: Dict[str, Any]) -> None:
    """
    Process sensor data from Matter device.
    
    Args:
        node_id: Matter device node identifier
        data: Sensor data dictionary
    """
    # Implementation
```

### Shell Scripts

- Use `#!/bin/bash` shebang
- Include usage comments
- Check return codes
- Quote variables: `"$variable"`
- Use `set -e` for error handling

### Docker

- Use multi-stage builds where beneficial
- Keep images small (prefer alpine/slim bases)
- Include health checks
- Document environment variables
- Use specific version tags, not `latest`

### Documentation

- Write in clear, concise English
- Include code examples
- Add screenshots for visual features
- Keep README.md up to date
- Update relevant guides in `docs/`

## Commit Messages

Follow conventional commits format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance tasks
- `ci`: CI/CD changes

### Examples

```
feat(bridge): add Home Assistant MQTT discovery

Implement auto-discovery for Home Assistant by publishing
device configuration to homeassistant/ topics.

Closes #42
```

```
fix(ipv6): correct kernel parameter for router advertisements

Changed net.ipv6.conf.all.accept_ra to net.ipv6.conf.eth0.accept_ra
for proper IPv6 routing on Raspberry Pi.

Fixes #38
```

## Pull Request Process

1. **Update documentation** - Ensure README.md and relevant docs reflect your changes
2. **Test on hardware** - If possible, test on actual Raspberry Pi with Matter devices
3. **Update CHANGELOG** - Add entry describing your changes (if applicable)
4. **Link issues** - Reference related issues in PR description
5. **Request review** - Maintainers will review and provide feedback
6. **Address feedback** - Make requested changes and update PR
7. **Merge** - Once approved, your PR will be merged

### PR Checklist

- [ ] Code follows project style guidelines
- [ ] Documentation updated
- [ ] Tested on Raspberry Pi (if hardware-related)
- [ ] Docker containers build successfully
- [ ] MQTT topics work as expected
- [ ] No breaking changes (or documented if necessary)
- [ ] Commit messages follow conventional format

## Project Structure

```
matter2mqtt/
├── bridge/              # Current Matter-MQTT bridge (v2)
├── bridge-legacy/       # Legacy implementation
├── config/              # Configuration templates
├── scripts/             # Utility scripts
├── docs/                # Documentation
└── .github/             # GitHub templates and workflows
```

When contributing, place files in appropriate directories:
- Bridge code → `bridge/`
- Scripts → `scripts/`
- Documentation → `docs/`
- Configuration → `config/`

## Questions?

- Check existing [issues](https://github.com/jenicek001/matter2mqtt/issues)
- Review [documentation](docs/)
- Open a [discussion](https://github.com/jenicek001/matter2mqtt/discussions) (if enabled)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing to matter2mqtt!** 🚀
