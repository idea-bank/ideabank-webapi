"""Tests for eraser endpoint handler"""

import pytest
import faker
from unittest.mock import patch
from sqlalchemy import create_engine
from fastapi import status
from ideabank_webapi.handlers import EndpointHandlerStatus
from ideabank_webapi.handlers.erasers import (
        StopFollowingAccountHandler,
        StopLikingConceptHandler
        )
from ideabank_webapi.handlers.preprocessors import AuthorizationRequired
from ideabank_webapi.services import (
        QueryService,
        RegisteredService
        )
from ideabank_webapi.models import (
        UnfollowRequest,
        UnlikeRequest,
        EndpointInformationalMessage,
        EndpointErrorMessage,
        )
from ideabank_webapi.exceptions import NotAuthorizedError, BaseIdeaBankAPIException


@pytest.fixture
def test_unfollow_request(test_auth_token, faker):
    return UnfollowRequest(
            auth_token=test_auth_token,
            follower=faker.user_name(),
            followee=faker.user_name()
            )


@pytest.fixture
def test_unlike_request(test_auth_token, faker):
    return UnlikeRequest(
            auth_token=test_auth_token,
            user_liking=faker.user_name(),
            concept_liked=f'{faker.user_name()}/{faker.domain_word()}'
            )


@patch.object(QueryService, 'ENGINE', create_engine('sqlite:///:memory:', echo=True))
@patch.object(QueryService, 'exec_next')
@patch.object(QueryService, 'results')
class TestStopFollowingHandler:

    def setup_method(self):
        self.handler = StopFollowingAccountHandler()
        self.handler.use_service(RegisteredService.ENGAGE_DS)

    @patch.object(AuthorizationRequired, '_check_if_authorized')
    def test_processing_unfollow_request(
            self,
            mock_auth_check,
            mock_query_results,
            mock_query,
            test_unfollow_request
            ):
        self.handler.receive(test_unfollow_request)
        self.handler.status == EndpointHandlerStatus.COMPLETE
        self.handler.result.code == status.HTTP_200_OK
        self.handler.result.body == EndpointInformationalMessage(
                msg=f"{test_unfollow_request.follower} is no longer following {test_unfollow_request.followee}"
                )

    @pytest.mark.parametrize("err_type, err_msg", [
        (NotAuthorizedError, 'Invalid token presented'),
        (NotAuthorizedError, 'Unable to verify token ownership')
        ])
    @patch.object(AuthorizationRequired, '_check_if_authorized')
    def test_unauthorized_unfollow_request(
            self,
            mock_auth_check,
            mock_query_results,
            mock_query,
            test_unfollow_request,
            err_type,
            err_msg
            ):
        mock_auth_check.side_effect = err_type(err_msg)
        self.handler.receive(test_unfollow_request)
        self.handler.status == EndpointHandlerStatus.ERROR
        self.handler.result.code == status.HTTP_401_UNAUTHORIZED
        self.handler.result.body == EndpointErrorMessage(err_msg=err_msg)

    @patch.object(
            StopFollowingAccountHandler,
            '_do_data_ops',
            side_effect=BaseIdeaBankAPIException("Really obscure error")
        )
    @patch.object(AuthorizationRequired, '_check_if_authorized')
    def test_a_really_messed_up_scenario(
            self,
            mock_auth_check,
            mock_data_ops,
            mock_query_result,
            mock_query,
            test_unfollow_request
            ):
        self.handler.receive(test_unfollow_request)
        assert self.handler.status == EndpointHandlerStatus.ERROR
        assert self.handler.result.code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert self.handler.result.body == EndpointErrorMessage(
                err_msg='Really obscure error'
                )


@patch.object(QueryService, 'ENGINE', create_engine('sqlite:///:memory:', echo=True))
@patch.object(QueryService, 'exec_next')
@patch.object(QueryService, 'results')
class TestStopLikingHandler:

    def setup_method(self):
        self.handler = StopLikingConceptHandler()
        self.handler.use_service(RegisteredService.ENGAGE_DS)

    @patch.object(AuthorizationRequired, '_check_if_authorized')
    def test_processing_unfollow_request(
            self,
            mock_auth_check,
            mock_query_results,
            mock_query,
            test_unlike_request
            ):
        self.handler.receive(test_unlike_request)
        self.handler.status == EndpointHandlerStatus.COMPLETE
        self.handler.result.code == status.HTTP_200_OK
        self.handler.result.body == EndpointInformationalMessage(
                msg=f"{test_unlike_request.user_liking} no longer likes {test_unlike_request.concept_liked}"
                )

    @pytest.mark.parametrize("err_type, err_msg", [
        (NotAuthorizedError, 'Invalid token presented'),
        (NotAuthorizedError, 'Unable to verify token ownership')
        ])
    @patch.object(AuthorizationRequired, '_check_if_authorized')
    def test_unauthorized_unfollow_request(
            self,
            mock_auth_check,
            mock_query_results,
            mock_query,
            test_unlike_request,
            err_type,
            err_msg
            ):
        mock_auth_check.side_effect = err_type(err_msg)
        self.handler.receive(test_unlike_request)
        self.handler.status == EndpointHandlerStatus.ERROR
        self.handler.result.code == status.HTTP_401_UNAUTHORIZED
        self.handler.result.body == EndpointErrorMessage(err_msg=err_msg)

    @patch.object(
            StopLikingConceptHandler,
            '_do_data_ops',
            side_effect=BaseIdeaBankAPIException("Really obscure error")
        )
    @patch.object(AuthorizationRequired, '_check_if_authorized')
    def test_a_really_messed_up_scenario(
            self,
            mock_auth_check,
            mock_data_ops,
            mock_query_result,
            mock_query,
            test_unlike_request
            ):
        self.handler.receive(test_unlike_request)
        assert self.handler.status == EndpointHandlerStatus.ERROR
        assert self.handler.result.code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert self.handler.result.body == EndpointErrorMessage(
                err_msg='Really obscure error'
                )
