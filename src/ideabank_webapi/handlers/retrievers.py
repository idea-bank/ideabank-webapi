"""
    :module name: retrievers
    :module summary: endpoint classes that deal with data retrieval
    :module author: Nathan Mendoza (nathancm@uci.edu)
"""

import logging
import hashlib
import secrets
import datetime
import json
from typing import Union, List

from sqlalchemy.exc import NoResultFound
from fastapi import status
from treelib import Tree
import jwt

from . import BaseEndpointHandler
from ..config import ServiceConfig
from ..services import RegisteredService
from ..models import (
        CredentialSet,
        AccountRecord,
        AuthorizationToken,
        ProfileView,
        ConceptRequest,
        ConceptSimpleView,
        ConceptFullView,
        ConceptSearchQuery,
        ConceptLineage,
        AccountFollowingRecord,
        ConceptLikingRecord,
        ConceptComment,
        ConceptCommentThreads,
        EndpointErrorMessage,
        EndpointInformationalMessage,
        EndpointResponse,
        )
from ..exceptions import (
        InvalidCredentialsException,
        BaseIdeaBankAPIException,
        RequestedDataNotFound
    )

LOGGER = logging.getLogger(__name__)


class AuthenticationHandler(BaseEndpointHandler):
    """Endpoint handler dealing into account authenticaiton"""

    def _do_data_ops(self, request: CredentialSet) -> str:
        try:
            LOGGER.info(
                    "Looking up account information: %s",
                    request.display_name
                    )
            with self.get_service(RegisteredService.ACCOUNTS_DS) as service:
                service.add_query(service.fetch_authentication_information(
                        display_name=request.display_name,
                    ))
                service.exec_next()
                result = service.results.one()
                self.__verify_credentials(request, result)
                return result.display_name
        except NoResultFound as err:
            LOGGER.error(
                    "No account record found: %s",
                    request.display_name
                    )
            raise InvalidCredentialsException(
                    "Invalid display name or password"
                    ) from err

    def _build_success_response(self, requested_data: str):
        self._result = EndpointResponse(
                code=status.HTTP_200_OK,
                body=AuthorizationToken(
                    token=self.__generate_token(requested_data),
                    presenter=requested_data
                    )
                )

    def _build_error_response(self, exc: BaseIdeaBankAPIException):
        if isinstance(exc, InvalidCredentialsException):
            self._result = EndpointResponse(
                    code=status.HTTP_401_UNAUTHORIZED,
                    body=EndpointErrorMessage(
                        err_msg=str(exc)
                        )
                    )
        else:
            super()._build_error_response(exc)

    def __verify_credentials(
            self,
            provided: CredentialSet,
            oracle: AccountRecord
            ):
        LOGGER.info("Comparing provided credentials to stored")
        provided_hash = hashlib.sha256(
                f'{provided.password}{oracle.salt_value}'.encode('utf-8')
                ).hexdigest()
        if secrets.compare_digest(provided_hash, oracle.password_hash):
            LOGGER.debug("Provided credentials match")
            return
        LOGGER.debug("Provided credentials did not match records")
        raise InvalidCredentialsException("Invalid display name or password")

    def __generate_token(self, owner: str) -> str:
        claims = {
                'username': owner,
                'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7),
                'nbf': datetime.datetime.utcnow() + datetime.timedelta(seconds=2)
                }
        return jwt.encode(
                claims,
                ServiceConfig.AuthKey.JWT_SIGNER,
                ServiceConfig.AuthKey.JWT_HASHER
                )


class ProfileRetrievalHandler(BaseEndpointHandler):
    """Endpoint handler dealing with profile retrievals"""

    def _do_data_ops(self, request: str) -> ProfileView:
        try:
            LOGGER.info("Looking up profile information: %s", request)
            with self.get_service(RegisteredService.ACCOUNTS_DS) as service:
                service.add_query(service.fetch_account_profile(
                    display_name=request
                    ))
                service.exec_next()
                result = service.results.one()
                return ProfileView(
                    preferred_name=result.preferred_name,
                    biography=result.biography,
                    avatar_url=service.share_item(f'avatars/{request}')
                        )
        except NoResultFound as err:
            LOGGER.error("No account record found: %s", request)
            raise RequestedDataNotFound(
                    f'Profile for {request} is not available'
                    ) from err

    def _build_success_response(self, requested_data: ProfileView):
        self._result = EndpointResponse(
                code=status.HTTP_200_OK,
                body=requested_data
                )

    def _build_error_response(self, exc: BaseIdeaBankAPIException):
        if isinstance(exc, RequestedDataNotFound):
            self._result = EndpointResponse(
                    code=status.HTTP_404_NOT_FOUND,
                    body=EndpointErrorMessage(
                        err_msg=str(exc)
                        )
                    )
        else:
            super()._build_error_response(exc)


class SpecificConceptRetrievalHandler(BaseEndpointHandler):
    """Handler for dealing with requests for a particular concept"""

    def _do_data_ops(self, request: ConceptRequest) -> ConceptSimpleView:
        LOGGER.info(
                "Searching for specific concept: %s/%s",
                request.author,
                request.title
                )
        try:
            with self.get_service(RegisteredService.CONCEPTS_DS) as service:
                service.add_query(service.find_exact_concept(
                    title=request.title,
                    author=request.author
                    ))
                service.exec_next()
                result = service.results.one()
                if request.simple:
                    return ConceptSimpleView(
                            identifier=f'{result.author}/{result.title}',
                            thumbnail_url=service.share_item(
                                f'thumbnails/{result.author}/{result.title}'
                                )
                            )
                return ConceptFullView(
                        author=result.author,
                        title=result.title,
                        description=result.description,
                        diagram=json.dumps(result.diagram),
                        thumbnail_url=service.share_item(
                            f'thumbnails/{result.author}/{result.title}'
                            )
                        )
        except NoResultFound as err:
            LOGGER.error(
                    "Did not find a concept matching %s/%s",
                    request.author,
                    request.title
                    )
            raise RequestedDataNotFound(
                    f"No match for `{request.author}/{request.title}`"
                    ) from err

    def _build_success_response(self, requested_data: Union[ConceptFullView, ConceptSimpleView]):
        LOGGER.info("Found a matching concept")
        self._result = EndpointResponse(
                code=status.HTTP_200_OK,
                body=requested_data
                )

    def _build_error_response(self, exc: BaseIdeaBankAPIException):
        if isinstance(exc, RequestedDataNotFound):
            LOGGER.error("Did not find a matching concept")
            self._result = EndpointResponse(
                    code=status.HTTP_404_NOT_FOUND,
                    body=EndpointErrorMessage(err_msg=str(exc))
                    )
        else:
            super()._build_error_response(exc)


class ConceptSearchResultHandler(BaseEndpointHandler):
    """Handler for dealing with search queries for relevant queries"""

    def _do_data_ops(self, request: ConceptSearchQuery) -> List[ConceptSimpleView]:
        LOGGER.info(
                "Searching for concepts matching the following criteria:\n%s",
                request.json(indent=4)
                )
        with self.get_service(RegisteredService.CONCEPTS_DS) as service:
            service.add_query(service.query_concepts(
                author=request.author,
                title=request.title,
                not_before=request.not_before,
                not_after=request.not_after,
                fuzzy=request.fuzzy
                ))
            service.exec_next()
            return [
                    ConceptSimpleView(
                        identifier=result.identifier,
                        thumbnail_url=service.share_item(
                            f'thumbnails/{result.identifier}'
                            )

                        )
                    for result in service.results.all()
                    ]

    def _build_success_response(self, requested_data: List[ConceptSimpleView]):
        self._result = EndpointResponse(
                code=status.HTTP_200_OK,
                body=requested_data
                )

    def _build_error_response(self, exc: BaseIdeaBankAPIException):  # pylint:disable=useless-parent-delegation
        super()._build_error_response(exc)


class ConceptLineageHandler(BaseEndpointHandler):
    """Endpoint handler for dealing with concept lineage retrieval"""

    def _do_data_ops(self, request: ConceptRequest) -> ConceptLineage:
        LOGGER.info(
                "Building lineage for `%s/%s`",
                request.author,
                request.title
                )
        focus = f'{request.author}/{request.title}'
        try:
            with self.get_service(RegisteredService.CONCEPTS_DS) as service:
                service.add_query(service.find_exact_concept(
                    author=request.author,
                    title=request.title
                    ))
                service.exec_next()
                service.results.one()  # Ensure it exists
                lineage = Tree()
                lineage.create_node(
                    tag=focus,
                    identifier=focus,
                    data=ConceptSimpleView(
                        identifier=focus,
                        thumbnail_url=service.share_item(
                            f'thumbnails/{focus}'
                            )
                        )
                    )
                service.add_query(service.find_parent_ideas(
                    identifier=focus,
                    depth=10
                    ))
                service.exec_next()
                for parent in service.results.all():
                    new_lineage = Tree()
                    new_lineage.create_node(
                            tag=parent.ancestor,
                            identifier=parent.ancestor,
                            data=ConceptSimpleView(
                                identifier=parent.ancestor,
                                thumbnail_url=service.share_item(
                                    f'thumbnails/{parent.ancestor}'
                                    )
                                )
                            )
                    new_lineage.paste(parent.ancestor, lineage)
                    lineage = new_lineage

                service.add_query(service.find_child_ideas(
                    identifier=focus,
                    depth=10
                    ))
                service.exec_next()
                for child in service.results.all():
                    lineage.create_node(
                            tag=child.descendant,
                            identifier=child.descendant,
                            parent=child.ancestor,
                            data=ConceptSimpleView(
                                identifier=child.descendant,
                                thumbnail_url=service.share_item(
                                    f'thumbnails/{child.descendant}'
                                    )
                                )
                            )
            return ConceptLineage(
                    nodes=lineage.size(),
                    lineage=lineage.to_dict(with_data=True)
                    )
        except NoResultFound as err:
            LOGGER.error(
                    "No concept record found for `%s/%s`. Unable to build lineage",
                    request.author,
                    request.title
                    )
            raise RequestedDataNotFound(
                    f"Could not build the lineage for {request.author}/{request.title}"
                    ) from err

    def _build_success_response(self, requested_data: ConceptLineage):
        LOGGER.info("Lineage successfully obtained")
        self._result = EndpointResponse(
                code=status.HTTP_200_OK,
                body=requested_data
                )

    def _build_error_response(self, exc: BaseException):
        if isinstance(exc, RequestedDataNotFound):
            LOGGER.error("No lineage tree resulted from build process")
            self._result = EndpointResponse(
                    code=status.HTTP_404_NOT_FOUND,
                    body=EndpointErrorMessage(
                        err_msg=str(exc)
                        )
                    )
        else:
            super()._build_error_response(exc)


class CheckFollowingStatusHandler(BaseEndpointHandler):
    """Endpoint handler dealing with checking if a user follows another"""

    def _do_data_ops(self, request: AccountFollowingRecord) -> EndpointInformationalMessage:
        LOGGER.info(
                "Checking if %s follows %s",
                request.follower,
                request.followee
                )
        try:
            with self.get_service(RegisteredService.ENGAGE_DS) as service:
                service.add_query(service.check_following(
                    follower=request.follower,
                    followee=request.followee
                    ))
                service.exec_next()
                service.results.one()
                return EndpointInformationalMessage(
                        msg=f"{request.follower} is following {request.followee}"
                        )
        except NoResultFound as err:
            LOGGER.error("Could not find a matching follow record")
            raise RequestedDataNotFound(
                    f"{request.follower} is not following {request.followee}"
                    ) from err

    def _build_success_response(self, requested_data: EndpointInformationalMessage):
        self._result = EndpointResponse(
                code=status.HTTP_200_OK,
                body=requested_data
                )

    def _build_error_response(self, exc: BaseIdeaBankAPIException):
        if isinstance(exc, RequestedDataNotFound):
            self._result = EndpointResponse(
                    code=status.HTTP_404_NOT_FOUND,
                    body=EndpointErrorMessage(
                        err_msg=str(exc)
                        )
                    )
        else:
            super()._build_error_response(exc)


class CheckLikingStatusHandler(BaseEndpointHandler):
    """Endpoint handler dealing with checking if a user likes a concept"""

    def _do_data_ops(self, request: ConceptLikingRecord) -> EndpointInformationalMessage:
        LOGGER.info(
                "Checking if %s likes %s",
                request.user_liking,
                request.concept_liked
                )
        try:
            with self.get_service(RegisteredService.ENGAGE_DS) as service:
                service.add_query(service.check_liking(
                    account=request.user_liking,
                    concept=request.concept_liked
                    ))
                service.exec_next()
                service.results.one()
                return EndpointInformationalMessage(
                        msg=f"{request.user_liking} does like {request.concept_liked}"
                        )
        except NoResultFound as err:
            LOGGER.error("Could not find a matching liking record")
            raise RequestedDataNotFound(
                    f"{request.user_liking} does not like {request.concept_liked}"
                    ) from err

    def _build_success_response(self, requested_data: EndpointInformationalMessage):
        self._result = EndpointResponse(
                code=status.HTTP_200_OK,
                body=requested_data
                )

    def _build_error_response(self, exc: BaseIdeaBankAPIException):
        if isinstance(exc, RequestedDataNotFound):
            self._result = EndpointResponse(
                    code=status.HTTP_404_NOT_FOUND,
                    body=EndpointErrorMessage(
                        err_msg=str(exc)
                        )
                    )
        else:
            super()._build_error_response(exc)


class ConceptCommentsSectionHandler(BaseEndpointHandler):
    """Endpoint handler for retrieving the comments section of a concept"""

    def _do_data_ops(self, request: ConceptRequest) -> ConceptCommentThreads:
        comment_tree = ConceptCommentThreads(threads=[])
        comment_tree.threads.extend(self.__thread_starts(
            concept_id=f'{request.author}/{request.title}'
            ))
        for thread in comment_tree.threads:
            self.__gather_responses(
                    concept_id=f'{request.author}/{request.title}',
                    current_thread=thread
                    )
        return comment_tree

    def _build_success_response(self, requested_data: ConceptCommentThreads):
        self._result = EndpointResponse(
                code=status.HTTP_200_OK,
                body=requested_data
                )

    def _build_error_response(self, exc: BaseIdeaBankAPIException):  # pylint:disable=useless-parent-delegation
        super()._build_error_response(exc)

    def __thread_starts(self, concept_id: str):
        with self.get_service(RegisteredService.ENGAGE_DS) as service:
            service.add_query(service.comments_on(concept_id))
            service.exec_next()
            return [
                    ConceptComment(
                        comment_id=c.comment_id,
                        comment_author=c.comment_by,
                        comment_text=c.free_text
                        )
                    for c in service.results.all()
                    ]

    def __gather_responses(self, concept_id: str, current_thread: ConceptComment):
        with self.get_service(RegisteredService.ENGAGE_DS) as service:
            service.add_query(service.comments_on(
                concept_id=concept_id,
                response_to=current_thread.comment_id
                ))
            service.exec_next()
            current_thread.responses.extend(
                    [
                        ConceptComment(
                            comment_id=c.comment_id,
                            comment_author=c.comment_by,
                            comment_text=c.free_text
                            )
                        for c in service.results.all()
                        ]
                    )
        for subthread in current_thread.responses:
            self.__gather_responses(concept_id, subthread)
