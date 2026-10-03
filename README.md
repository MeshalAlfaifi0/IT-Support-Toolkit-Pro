# IT Operations Console

A Windows desktop application for IT support technicians, built with Python and PySide6. It brings device diagnostics, network tools, maintenance workflows, and local security checks into one Arabic and English interface.

**Author:** [Meshal Alfaifi](https://github.com/MeshalAlfaifi0) · [LinkedIn](https://www.linkedin.com/in/meshal-alfaifi-cs)

## Features

- **Device diagnostics:** hardware and operating system information, driver diagnostics, and connected device inventory.
- **Health checks:** system health indicators, recommendations, and clear separation between failed checks and detected issues.
- **Network tools:** adapter information, IPv4 configuration validation, connectivity diagnostics, and DNS utilities.
- **Printers and scanners:** device status, print queue inspection, and administrative maintenance tools.
- **Windows maintenance:** service management, repair tools, and temporary file cleanup with protected application paths.
- **Domain tools:** domain information and administrative workflows.
- **Security indicators:** separate firewall profile status, BitLocker encryption and protection status, and other local checks.
- **Daily workflow:** command tools, an action history, persistent preferences, light and dark themes, and Arabic/English layouts.

The History page displays action logs. Settings contains appearance, language, and application information.

## Requirements

- Windows 10 or Windows 11. The current build was tested on Windows 11.
- Python 3.12, 64-bit, when running or building from source.
- Administrator privileges for operations that change system configuration. Ordinary application startup does not require elevation.

The main runtime dependencies are PySide6, psutil, pywin32, WMI, ReportLab, openpyxl, and Pillow. Their tested direct versions are recorded in [requirements-lock.txt](requirements-lock.txt). Native Python packages must match the interpreter version and architecture.

## Run the application

### Compiled executable

If you already have a compiled executable, open it directly. Python is not required to run the bundled application.

Download **IT-Operations-Console-Windows.exe** from the [latest Windows release](https://github.com/MeshalAlfaifi0/IT-Support-Toolkit-Pro/releases/latest). Open it directly; the executable bundles its runtime dependencies.

Historical backups, personal databases, application logs and virtual environment folders are kept in private storage and are not distributed with the public project.

The existing local build is:

```text
dist/IT-Operations-Console-Organized-20261003.exe
```

From the project directory in PowerShell:

```powershell
& ".\dist\IT-Operations-Console-Organized-20261003.exe"
```

Build outputs are excluded from Git. A source checkout must be installed or built using the instructions below.

### From source

Open PowerShell in the project directory, then create a fresh virtual environment:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe app.py
```

Using the virtual environment's executable directly avoids requiring shell activation.

## Project structure

```text
app.py                         Application entry point
src/
  core/                        Windows operations and diagnostic rules
  database/                    SQLite schema, connections, and persistence
  ui/                          Main window and individual PySide6 pages
  utils/                       Paths, translations, themes, workers, and commands
  reports/                     Standalone JSON, CSV, and PDF report modules
tests/                         Targeted core, persistence, report, and UI tests
scripts/                       Quality checks, tests, builds, and source packaging
packaging/                     PyInstaller configuration
docs/                          Architecture, development, and release guides
.github/                       CI workflow and contribution templates
```

Source comments and the detailed development guides are written in Arabic to make the code easier to follow and maintain:

- [Architecture and file map](docs/ARCHITECTURE.ar.md)
- [Development and testing](docs/DEVELOPMENT.ar.md)
- [Build and release guide](docs/RELEASE.ar.md)
- [Contributing](CONTRIBUTING.md)
- [Security reporting](SECURITY.md)

Report modules remain available for development and testing; the current interface does not expose a reports/export page.

## Development and testing

Install the development tools and run the project checks:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe scripts/check_project.py
```

The checker validates source syntax, checks known private-key/token patterns, runs Ruff linting and formatting checks, and executes the test suite in Arabic and in English at 150% scaling. Test data is isolated from the user's normal application data.

To run individual test configurations:

```powershell
.\.venv\Scripts\python.exe scripts/run_tests.py --language ar
.\.venv\Scripts\python.exe scripts/run_tests.py --language en --scale 1.5
```

Network configuration changes, domain actions, and printer queue mutations are tested with mocks. Cleanup tests operate on disposable test files.

### Startup and persistence checks

```powershell
.\.venv\Scripts\python.exe scripts/smoke_test.py
.\.venv\Scripts\python.exe scripts/smoke_test.py --exe dist/IT-Operations-Console-Organized-20261003.exe
```

These checks construct all application pages, close the process, and restart it to verify saved language and theme settings in temporary storage. They use Qt's offscreen mode; inspect the visible interface separately when preparing a release.

The GitHub Actions workflow runs both test configurations on Windows. Its optional release job builds the EXE, checks source and executable startup twice with saved preferences, and publishes only the verified executable. To request a release, run the workflow manually with `publish_exe` enabled, or include `[release-exe]` in a push commit message on `main`. Ordinary pushes and pull requests only run checks.

## Build an executable

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\scripts\build_exe.bat
```

The build script writes a single-file executable to `dist/` with a new name and refuses to overwrite an existing executable. To choose the name:

```powershell
$env:IT_TOOLKIT_BUILD_NAME = "IT-Operations-Console-Release"
.\scripts\build_exe.bat
```

Build settings live in [packaging/IT-Operations-Console.spec](packaging/IT-Operations-Console.spec). The root-level `IT-Support-Toolkit-Pro.spec` remains a compatibility entry point for older build commands.

`requirements-lock.txt` pins direct runtime dependencies; it is not a complete transitive dependency lock.

## Application data

Settings, the SQLite database, logs, and generated reports are stored under:

```text
%LOCALAPPDATA%\IT Support Toolkit Pro
```

The storage directory keeps its original name so existing data remains accessible after the application was renamed. It is independent of PyInstaller's temporary extraction directory.

For an isolated development environment, set `IT_TOOLKIT_DATA_DIR` to a dedicated folder before starting the application. Existing recoverable data may be migrated when the destination has no database; use the supplied test runners for controlled test fixtures.

## Preparing source for GitHub

Create a clean source archive:

```powershell
.\.venv\Scripts\python.exe scripts/package_source.py
```

The archive includes an explicit set of source files, documentation, tests, and project configuration. Databases, logs, backups, virtual environments, binaries, and generated artifacts are excluded.

Review the files selected by Git before committing. Do not upload the entire working directory indiscriminately. Keep compiled executables separate from the source repository, for example as release assets.

## Diagnostic scope

- An unknown result means the check could not determine the state. It does not establish that the system is healthy or that a fault exists.
- Windows Update service status is separate from patch recency. HotFix age is an indicative signal rather than a complete update assessment.
- Local security indicators do not provide a compliance certification or prove that a device has no vulnerabilities.
- Some Windows and WMI operations require elevation or take time to complete. Closing the application waits for active workers to finish safely.

## License

A license has not been selected for this project. No license file is included.
