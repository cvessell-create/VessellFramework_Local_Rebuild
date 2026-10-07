import json
from pathlib import Path

import pytest


@pytest.fixture
def field_assessment():
    return json.loads((Path(__file__).parent / "fixtures/field-inquiry.json").read_text())
