# QA Automation Framework

This is a basic QA automation framework for testing.
Use python 3.12 for UI tests (https://www.python.org/downloads/)

## Setup

1. Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies.

In projects work tree execute:
```bash
pip install -r requirements.txt
# for UI tests:
pip install playwright pytest-playwright
python -m playwright install
```

3. Install the product

In projects work tree execute:
```bash
pip install .
```

## Running Tests

### For services tests:

#### Prerequisites: SSH Key Authentication Setup (REQUIRED)

**IMPORTANT**: SSH key-based authentication is mandatory for running service tests. Password authentication is not supported.

1. Generate SSH key pair (if you don't have one):
```bash
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
```

2. Copy your public key to the mirada host:

**Option A: Using ssh-copy-id (Linux/macOS/WSL):**
```bash
ssh-copy-id codemaster@[ip_mirada]
```

**Option B: Manual setup (Windows/Universal):**
```powershell
# On Windows, display your public key:
type $env:USERPROFILE\.ssh\id_rsa.pub

# Copy the output, then connect to the mirada host and run:
ssh codemaster@[ip_mirada]

# On the remote host, create .ssh directory and set permissions:
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Add your public key to authorized_keys:
echo "YOUR_COPIED_PUBLIC_KEY" >> ~/.ssh/authorized_keys

# Set strict permissions for authorized_keys:
chmod 600 ~/.ssh/authorized_keys
```

3. Verify passwordless access:
```bash
ssh codemaster@[ip_mirada]
```
This command should connect without prompting for a password.

#### Stage 1: Mirada Agent (required)
- Agent must be installed on the mirada host before running tests.
- Agent documentation and usage are inside the `mirada-agent` folder: https://gitlab.codemaster.pro/ngfw/qa-auto/-/tree/main/mirada-agent (README inside).

##### Agent Deployment

Use the automated deployment utility:

```bash
# Simple deployment
python services/deploy_agent.py --mirada-host=[ip_mirada]

# With verbose output
python services/deploy_agent.py --mirada-host=[ip_mirada] --verbose
```

The utility automatically:
- Copies the `mirada-agent` folder to the specified host via SCP
- Excludes service folders and caches (`__pycache__`, `.git`, `.pytest_cache`, etc.)
- Sets execution permissions for scripts (`start.sh`, `stop.sh`, `restart.sh`)
- Converts Windows line endings to Unix format
- Verifies successful deployment

After deployment, start the agent on the remote host:
```bash
ssh codemaster@[ip_mirada]
cd /home/codemaster/mirada-agent
sudo ./start.sh
```

#### Stage 2: Services tests

##### Test Execution

All service tests require the `--mirada-host` parameter. The framework automatically creates and manages SSH tunnels using your configured SSH keys.

**Basic Usage:**
```bash
# Run tests for a specific service
pytest services/services-monitor --mirada-host=[ip_mirada]

# Run specific test
pytest services/services-monitor/test_services.py::test_services_parametrized --mirada-host=[ip_mirada]

# Run tests for any service
pytest services/objects --mirada-host=[ip_mirada]
pytest services/cluster --mirada-host=[ip_mirada]

# Run all services tests
pytest services/ --mirada-host=[ip_mirada]
```

##### Using Command-Line Options
Customize tests with options like timeout.

| Option              | Description                     | Example                 |
|---------------------|---------------------------------|-------------------------|
| `--request-timeout` | Timeout for requests (seconds) | `--request-timeout=3`  |

**Example with options**:
```bash
pytest services/services-monitor --mirada-host=[ip_mirada] --request-timeout=30
```

##### Test Resumption and Logging

###### Resume Failed Tests with `--resume`
This parameter allows you to resume a previously failed test from the same point. This feature automatically detects and does not run tests that have already passed.

**Usage:**
```bash
# Resume failed tests from the last run
pytest services/services-monitor --mirada-host=[ip_mirada] --resume
```

###### Test Logging System
The framework automatically logs test results for tracking and analysis:

**Log Files:**
- `logs/failed_tests_YYYYMMDD_HHMMSS.log` - Contains failed test information with timestamps

**Log Format Example:**
```
=== FAILED TEST ===
Test: services/csi-server/test_auth.py::test_login_invalid_credentials
Time: 2025-10-08 14:35:59
Host: [ip_mirada]
Reason: AssertionError: Expected status 401, got 500
Traceback: [detailed error information]
==================
```

#### Special Case: Manager Reboot and Reset Tests

The `manager_reboot` test in `services/csi-server/manager_reboot.py` and `manager_reset` tests in `services/csi-server/manager_reset.py` are **CRITICAL** and require manual confirmation because they will **reboot/reset the system**.

**To run the reboot test**:
```bash
# Set confirmation environment variable
export MANUAL_TEST_CONFIRMATION=1

# Run only the reboot test
pytest services/csi-server/manager_reboot.py::test_manager_reboot_success

# Or run all tests in the file (reboot test will be last)
pytest services/csi-server/manager_reboot.py
```

**To skip the reboot test** (default behavior):
```bash
# Test will be skipped automatically
pytest services/csi-server/manager_reboot.py
```

**Available commands for the reboot test**:
- `test_manager_reboot_unauthorized` - Test without auth token
- `test_manager_reboot_invalid_token` - Test with invalid token  
- `test_manager_reboot_wrong_method` - Test with wrong HTTP method
- `test_manager_reboot_success` - **CRITICAL**: System reboot test (requires manual confirmation)

**To run the reset tests**:
```bash
# Set confirmation environment variable
export MANUAL_TEST_CONFIRMATION=1

# Run only specific reset test
pytest services/csi-server/manager_reset.py::test_manager_reset_success_no_payload
pytest services/csi-server/manager_reset.py::test_manager_reset_success_skip_homedir_true
pytest services/csi-server/manager_reset.py::test_manager_reset_success_skip_homedir_false

# Or run all tests in the file (reset tests will be last)
pytest services/csi-server/manager_reset.py
```

**To skip the reset tests** (default behavior):
```bash
# Tests will be skipped automatically
pytest services/csi-server/manager_reset.py
```

**Available commands for the reset tests**:
- `test_manager_reset_unauthorized` - Test without auth token
- `test_manager_reset_invalid_token` - Test with invalid token  
- `test_manager_reset_wrong_method` - Test with wrong HTTP method
- `test_manager_reset_success_no_payload` - **CRITICAL**: System reset test without payload (requires manual confirmation)
- `test_manager_reset_success_skip_homedir_true` - **CRITICAL**: System reset test with skip-homedir=true (requires manual confirmation)
- `test_manager_reset_success_skip_homedir_false` - **CRITICAL**: System reset test with skip-homedir=false (requires manual confirmation)

### For UI tests:
create admin user "auto_test" / "auto_test" on host

Edit file UI\creds.json:
```

{
    "admin": {
        "login": "auto_admin",          # Логин пользователя
        "password": "auto_admin",       # Пароль пользователя
        "ip": "10.200.103.35",          # ip адресс хоста
        "cluster_state": "standalone",  # состояние в кластере на выбор: "standalone" - машина не в кластере
                                        #                                "slave" - слэйв нода
                                        #                                "master" - мастер нода
        "type": "hardware",             # тип машины на выбор: "software" - SW
                                        #                      "hardware" - HW
        "email": "test@codemaster.pro"  # e-mail, куда будут отправляться электронные письма (раздел Аудит безопасности / Отчетность)
    },
    "user": {
        "login": "user",                # В текущей реализации не изменяется
        "password": "user"              # В текущей реализации не изменяется
    }
}
```

```bash
pytest UI --headed --slowmo 500                 # Start with visual display
pytest UI                                       # Start without visual display
pytest UI\security_audit\reports\test_create.py # Start specific test file
```

## Project Structure

- `services/` - Test files organized by service
- `conftest.py` - Pytest configuration and fixtures
- `pytest.ini` - Pytest settings
- `requirements.txt` - Project dependencies
- `setup.py` - Package configuration
- `constants.py` - Common constants and configuration values

## Структура

- `conftest.py`
