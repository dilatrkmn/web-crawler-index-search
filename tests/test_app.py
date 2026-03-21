import importlib.util

import pytest

pytestmark = pytest.mark.skipif(
    importlib.util.find_spec('flask') is None
    or importlib.util.find_spec('mysql') is None
    or importlib.util.find_spec('dotenv') is None
    or importlib.util.find_spec('flask_login') is None,
    reason='Flask/MySQL dependencies are not installed in this environment.',
)

if importlib.util.find_spec('flask') is not None:
    from crawler.app import create_app
else:
    create_app = None


def test_placeholder_when_dependencies_exist():
    if create_app is None:
        pytest.skip('Flask stack not installed.')
    assert callable(create_app)