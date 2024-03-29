"""Tests for the accounts service"""

from ideabank_webapi.services import AccountsDataService
import pytest


def test_account_has_all_parent_class_attributes():
    service = AccountsDataService()
    expected = ['_query_buffer', '_query_results', '_session', '_s3_client']
    assert all(attr in service.__dict__ for attr in expected)


@pytest.mark.parametrize("user, passwd, salt", [
    ('user1', 'passwd1', 'salt1'),
    ('user2', 'passwd2', 'salt2'),
    ('user3', 'passwd3', 'salt3')
])
def test_account_creation_query_builder(user, passwd, salt):
    stmt = AccountsDataService.create_account(user, passwd, salt)
    assert str(stmt) == 'INSERT INTO accounts' \
                        ' (display_name, preferred_name, biography, password_hash, salt_value, created_at, updated_at)' \
                        ' VALUES (:display_name, :preferred_name, :biography, :password_hash, :salt_value, :created_at, :updated_at)' \
                        ' RETURNING accounts.display_name'


@pytest.mark.parametrize("user", [
    'user1', 'user2', 'user3'
])
def test_authentication_query_builds(user):
    stmt = AccountsDataService.fetch_authentication_information(user)
    assert str(stmt) == 'SELECT accounts.display_name, accounts.password_hash, accounts.salt_value \n' \
                        'FROM accounts \n' \
                        'WHERE accounts.display_name = :display_name_1'


@pytest.mark.parametrize("user", [
    'user1', 'user2', 'user3'
    ])
def test_profile_fetch_query_builds(user):
    stmt = AccountsDataService.fetch_account_profile(user)
    assert str(stmt) == 'SELECT accounts.preferred_name, accounts.biography \n' \
                        'FROM accounts \n' \
                        'WHERE accounts.display_name = :display_name_1'
