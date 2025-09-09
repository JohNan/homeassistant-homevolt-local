## Running Tests

To run the test suite for this custom component, follow these steps.

### 1. Install Dependencies

First, ensure you have the development dependencies installed. From the root of the repository, run:

```bash
pip install -r requirements-dev.txt
```

### 2. Run Pytest

Once the dependencies are installed, you can run the tests using `pytest`. The `PYTHONPATH` needs to be set to the current directory for the tests to be able to locate the custom component modules.

Execute the following command from the root of the repository:

```bash
PYTHONPATH=. pytest
```
