import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from tests.integration.conftest import bearer

pytestmark = pytest.mark.anyio
CONTRACTS = Path(__file__).parents[2] / 'contracts'


async def test_me_matches_django_admin_contract(client, make_user, login):
    await make_user('anna@example.com')
    tokens = await login('anna@example.com')

    response = await client.get('/auth/me', headers=bearer(tokens))

    schema = json.loads((CONTRACTS / 'django_admin.auth_me.schema.json').read_text())
    Draft202012Validator(schema).validate(response.json())
