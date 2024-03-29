"""
    :module name: erasers
    :module summary: A collection of handlers that remove data records
    :module author: Nathan Mendoza (nathancm@uci.edu)
"""

import logging

from fastapi import status

from .preprocessors import AuthorizationRequired
from ..services import RegisteredService
from ..models import (
    UnfollowRequest,
    UnlikeRequest,
    EndpointInformationalMessage,
    EndpointResponse
        )
from ..exceptions import BaseIdeaBankAPIException

LOGGER = logging.getLogger(__name__)


class StopFollowingAccountHandler(AuthorizationRequired):
    """Endpoint handler dealing with removing following records"""

    def _do_data_ops(self, request: UnfollowRequest) -> EndpointInformationalMessage:
        LOGGER.info(
                "Removing the following record %s <- %s",
                request.followee,
                request.follower
                )
        with self.get_service(RegisteredService.ENGAGE_DS) as service:
            service.add_query(service.revoke_following(
                follower=request.follower,
                followee=request.followee
                ))
            service.exec_next()

        return EndpointInformationalMessage(
                msg=f"{request.follower} is no longer following {request.followee}"
                )

    def _build_error_response(self, exc: BaseIdeaBankAPIException):  # pylint:disable=useless-parent-delegation
        super()._build_error_response(exc)

    def _build_success_response(self, requested_data: EndpointInformationalMessage):
        self._result = EndpointResponse(
                code=status.HTTP_200_OK,
                body=requested_data
                )


class StopLikingConceptHandler(AuthorizationRequired):
    """Endpoint handler dealing with removing liking records"""

    def _do_data_ops(self, request: UnlikeRequest) -> EndpointInformationalMessage:
        LOGGER.info(
                "Removing the liking record %s <- %s",
                request.concept_liked,
                request.user_liking
                )
        with self.get_service(RegisteredService.ENGAGE_DS) as service:
            service.add_query(service.revoke_liking(
                account_unliking=request.user_liking,
                concept_unliked=request.concept_liked
                ))
            service.exec_next()

        return EndpointInformationalMessage(
                msg=f"{request.user_liking} no longer likes {request.concept_liked}"
                )

    def _build_error_response(self, exc: BaseIdeaBankAPIException):  # pylint:disable=useless-parent-delegation
        super()._build_error_response(exc)

    def _build_success_response(self, requested_data: EndpointInformationalMessage):
        self._result = EndpointResponse(
                code=status.HTTP_200_OK,
                body=requested_data
                )
