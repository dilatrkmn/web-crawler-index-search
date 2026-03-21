import importlib.util

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec('flask') is None
    or importlib.util.find_spec('mysql') is None
    or importlib.util.find_spec('dotenv') is None
    or importlib.util.find_spec('flask_login') is None,
    reason='Integration test requires Flask/MySQL dependencies and a running MySQL database.',
)


def test_mysql_integration_placeholder():
    pytest.skip('Run this after installing requirements and configuring a local MySQL instance.')