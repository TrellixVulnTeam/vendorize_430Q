# Development setup

The recommended way is to install dependencies in a virtual environment:

    (vendorize) $ pip install -r requirements.txt .

# Testing

All tests are run via the Python unittest framework. To run all tests:

    python3 -m unittest discover tests -v

Or an individual test:

    python3 -m unittest run tests.test_processor -f

See the module's documentation for more details:

    python3 -m unittest --help
