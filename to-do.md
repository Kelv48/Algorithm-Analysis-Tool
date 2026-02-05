# Roadmap / Planned Improvements

This section outlines planned features, architectural decisions, and future improvements for the project. Items listed here are either under consideration or scheduled for future implementation.

---

## 1. Project Restructuring

### 1.1 Convert Test Code into Full Project Layout

Restructure the current test-based implementation into a standard Python project layout. This will improve maintainability, modularity, and scalability.

Planned changes include:

- Separating core logic, runtime counters, and CLI utilities
- Introducing a dedicated `src/` directory structure
- Adding a `tests/` directory for automated testing
- Preparing the project for packaging and distribution

---

## 2. Python Package & Versioning

### 2.1 Create an Installable Python Package

Convert the project into an installable Python package using modern packaging standards.

Planned tasks:

- Create `pyproject.toml` or `setup.py`
- Add versioning support
- Define package metadata (name, description, author)
- Configure build tools (setuptools / poetry)

---

### 2.2 Dependency Management

Establish a dependency management system to ensure reproducible builds and environments.

This includes:

- Defining required packages
- Creating a `requirements.txt` or dependency lock file
- Supporting virtual environments

---

## 3. Core Feature Expansion

### 3.1 Full File Analysis Support

Extend the analysis engine to operate on entire Python files instead of isolated functions.

This will allow:

- Whole-program instrumentation
- Cross-function operation tracking
- Realistic runtime behavior analysis

---

### 3.2 External File Input Support

Allow users to provide a target Python file as input to the tool.

Planned usage methods:

- Command-line argument input
- Programmatic API calls from external scripts
- Configuration file support

---

### 3.3 Comprehensive Documentation

Expand documentation to clearly describe:

- The purpose of each counter function
- The role of each AST transformation method
- Internal data flow and execution pipeline
- Usage examples and expected output

This will improve usability and academic reproducibility.

---

## 4. Entry Point Design

Investigate multiple entry point options for interacting with the tool.

Potential interfaces include:

- Command Line Interface (CLI)
- Python API module
- Script-based invocation
- Web-based interface (optional)

The final interface design will depend on deployment goals and user requirements.

---

## 5. Deployment & Hosting Strategy

Determine how the project will be deployed and served in production environments.

---

### 5.1 Continuous Integration (CI) Integration

Investigate linking the project to a Jenkins virtual machine for automated builds and updates.

Planned capabilities:

- Automatic testing on commits
- Build verification
- Deployment triggers

---

### 5.2 Virtual Machine Hosting

Explore hosting the project on a dedicated virtual machine.

This may include:

- Public access deployment
- Internal research environment hosting
- Remote API access

---

### 5.3 DNS & Networking Configuration

Clarify network requirements for project access and service discovery.

Topics to evaluate:

- Domain name registration vs internal DNS routing
- Service discovery mechanisms
- Public vs private access configuration

---

## Status

All items listed in this section are **under review or pending implementation** and may be adjusted based on project scope, performance requirements, and academic constraints.



What can be enterted into the tool that cant be coped with that we have no intention of evalutating
Given this basic machinery how useful will it be for a student

- Test streamlit components for thurs