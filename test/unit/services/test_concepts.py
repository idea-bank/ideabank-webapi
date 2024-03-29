"""Tests for concepts data service"""

import pytest
import datetime
from ideabank_webapi.services import ConceptsDataService
from ideabank_webapi.models.artifacts import FuzzyOption


def test_account_has_all_parent_class_attributes():
    service = ConceptsDataService()
    expected = ['_query_buffer', '_query_results', '_session', '_s3_client']
    assert all(attr in service.__dict__ for attr in expected)


def test_concept_creation_query_builds():
    stmt = ConceptsDataService.create_concept(
            title='atitle',
            author='anauthor',
            description='adescription',
            diagram={'key': 'value'}
            )
    assert str(stmt) == 'INSERT INTO concepts ' \
                        '(title, author, description, diagram, created_at, updated_at) VALUES ' \
                        '(:title, :author, :description, :diagram, :created_at, :updated_at) ' \
                        'RETURNING concepts.identifier'


def test_concept_find_query_builds():
    stmt = ConceptsDataService.find_exact_concept('atitle', 'anauthor')
    assert str(stmt) == 'SELECT concepts.author, concepts.title, concepts.description,' \
                        ' concepts.diagram \n' \
                        'FROM concepts \nWHERE concepts.title = :title_1 AND concepts.author = :author_1'


def test_concept_linking_query_builds():
    stmt = ConceptsDataService.link_existing_concept('parentid', 'childid')
    assert str(stmt) == 'INSERT INTO concept_links (ancestor, descendant) ' \
                        'VALUES (:ancestor, :descendant) ' \
                        'RETURNING concept_links.ancestor, concept_links.descendant'


@pytest.mark.parametrize("fuzzy", FuzzyOption)
def test_concept_query_result_builds(fuzzy):
    stmt = ConceptsDataService.query_concepts(
            'atitle',
            'anauthor',
            datetime.datetime.utcnow(),
            datetime.datetime.utcnow(),
            fuzzy
            )
    if fuzzy == FuzzyOption.ALL:
        assert str(stmt) == 'SELECT concepts.identifier \n' \
                            'FROM concepts \n' \
                            'WHERE concepts.author LIKE :author_1 AND ' \
                            'concepts.title LIKE :title_1 AND ' \
                            'concepts.updated_at > :updated_at_1 AND ' \
                            'concepts.updated_at < :updated_at_2'
    elif fuzzy == FuzzyOption.TITLE:
        assert str(stmt) == 'SELECT concepts.identifier \n' \
                            'FROM concepts \n' \
                            'WHERE concepts.author = :author_1 AND ' \
                            'concepts.title LIKE :title_1 AND ' \
                            'concepts.updated_at > :updated_at_1 AND ' \
                            'concepts.updated_at < :updated_at_2'
    elif fuzzy == FuzzyOption.AUTHOR:
        assert str(stmt) == 'SELECT concepts.identifier \n' \
                            'FROM concepts \n' \
                            'WHERE concepts.author LIKE :author_1 AND ' \
                            'concepts.title = :title_1 AND ' \
                            'concepts.updated_at > :updated_at_1 AND ' \
                            'concepts.updated_at < :updated_at_2'
    else:
        assert str(stmt) == 'SELECT concepts.identifier \n' \
                            'FROM concepts \n' \
                            'WHERE concepts.author = :author_1 AND ' \
                            'concepts.title = :title_1 AND ' \
                            'concepts.updated_at > :updated_at_1 AND ' \
                            'concepts.updated_at < :updated_at_2'


def test_concept_find_children_query_build():
    stmt = ConceptsDataService.find_child_ideas('testuser/sample-idea', 5)
    assert str(stmt) == 'WITH RECURSIVE anon_1(descendant, ancestor, depth) AS \n' \
                        '(SELECT concept_links.descendant AS descendant, concept_links.ancestor AS ancestor, :param_1 AS depth \n' \
                        'FROM concept_links \n' \
                        'WHERE concept_links.ancestor = :ancestor_1 ' \
                        'UNION ALL ' \
                        'SELECT concept_links.descendant AS descendant, concept_links.ancestor AS ancestor, anon_1.depth + :depth_1 AS anon_2 \n' \
                        'FROM concept_links, anon_1 \n' \
                        'WHERE concept_links.ancestor = anon_1.descendant)\n ' \
                        'SELECT anon_1.ancestor, anon_1.descendant \n' \
                        'FROM anon_1 \n' \
                        'WHERE anon_1.depth <= :depth_2 ORDER BY anon_1.depth'


def test_concept_find_parents_query_build():
    stmt = ConceptsDataService.find_parent_ideas('testuser/sample-idea', 5)
    assert str(stmt) == 'WITH RECURSIVE anon_1(descendant, ancestor, depth) AS \n' \
                        '(SELECT concept_links.descendant AS descendant, concept_links.ancestor AS ancestor, :param_1 AS depth \n' \
                        'FROM concept_links \n' \
                        'WHERE concept_links.descendant = :descendant_1 ' \
                        'UNION ALL ' \
                        'SELECT concept_links.descendant AS descendant, concept_links.ancestor AS ancestor, anon_1.depth + :depth_1 AS anon_2 \n' \
                        'FROM concept_links, anon_1 \n' \
                        'WHERE concept_links.descendant = anon_1.ancestor)\n ' \
                        'SELECT anon_1.ancestor, anon_1.descendant \n' \
                        'FROM anon_1 \n' \
                        'WHERE anon_1.depth <= :depth_2 ORDER BY anon_1.depth'
