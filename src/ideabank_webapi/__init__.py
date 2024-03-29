"""
    :module_name: ideabank_webapi
    :module_summary: An API for the services utilized by the Idea Bank application
    :module_author: Nathan Mendoza (nathancm@uci.edu)
"""

import logging
import datetime
from typing import Union, List

from fastapi import FastAPI, status, Header
from fastapi.responses import JSONResponse

from .handlers.factory import EndpointHandlerFactory
from .services import RegisteredService
from .models import (
        CredentialSet,
        AuthorizationToken,
        ProfileView,
        ConceptSimpleView,
        ConceptFullView,
        ConceptRequest,
        ConceptDataPayload,
        CreateConcept,
        ConceptLinkRecord,
        EstablishLink,
        ConceptSearchQuery,
        ConceptLineage,
        AccountFollowingRecord,
        FollowRequest,
        UnfollowRequest,
        ConceptLikingRecord,
        LikeRequest,
        UnlikeRequest,
        ConceptComment,
        CreateComment,
        EndpointErrorMessage,
        EndpointInformationalMessage
)
from .models.artifacts import FuzzyOption


class IdeabankAPI(FastAPI):
    """Extension of FastAPI application to include a factory object"""

    def __init__(self):
        super().__init__()
        self.endpoint_factory = EndpointHandlerFactory()


app = IdeabankAPI()

LOGGER = logging.getLogger(__name__)
LOG_HANDLER = logging.StreamHandler()
LOG_FORMAT = logging.Formatter(
        fmt='[%(asctime)s] [%(process)d] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S %z'
        )
LOGGER.setLevel(logging.DEBUG)
LOG_HANDLER.setLevel(logging.DEBUG)
LOG_HANDLER.setFormatter(LOG_FORMAT)
LOGGER.addHandler(LOG_HANDLER)


@app.post(
        "/accounts/create",
        status_code=status.HTTP_201_CREATED,
        responses={
            status.HTTP_201_CREATED: {
                'model': EndpointInformationalMessage
                },
            status.HTTP_403_FORBIDDEN: {
                'model': EndpointErrorMessage
                }
            }
        )
def create_account(
        new_account: CredentialSet,
        response: JSONResponse
        ):
    """Create a new account with the given display name and password if available"""
    handler = app.endpoint_factory.create_handler(
            'AccountCreationHandler',
            RegisteredService.ACCOUNTS_DS
            )
    handler.receive(new_account)
    response.status_code = handler.result.code
    return handler.result.body


@app.post(
        "/accounts/authenticate",
        responses={
            status.HTTP_200_OK: {
                'model': AuthorizationToken
                },
            status.HTTP_401_UNAUTHORIZED: {
                'model': EndpointErrorMessage
                }
            }
        )
def authenticate(
        credentials: CredentialSet,
        response: JSONResponse
        ):
    """
        Verify the provided credentials against stored version.
        Provides the client with an AuthorizationToken if correct
    """
    handler = app.endpoint_factory.create_handler(
            'AuthenticationHandler',
            RegisteredService.ACCOUNTS_DS
            )
    handler.receive(credentials)
    response.status_code = handler.result.code
    return handler.result.body


@app.get(
        "/accounts/{display_name}/profile",
        responses={
            status.HTTP_200_OK: {
                'model': ProfileView
                },
            status.HTTP_404_NOT_FOUND: {
                'model': EndpointErrorMessage
                }
            }
        )
def fetch_profile(
        display_name: str,
        response: JSONResponse
        ):
    """Fetches the profile view of the request display name if it exists"""
    handler = app.endpoint_factory.create_handler(
            'ProfileRetrievalHandler',
            RegisteredService.ACCOUNTS_DS
            )
    handler.receive(display_name)
    response.status_code = handler.result.code
    return handler.result.body


@app.post(
        "/concepts",
        status_code=status.HTTP_201_CREATED,
        responses={
            status.HTTP_201_CREATED: {
                'model': ConceptSimpleView
                },
            status.HTTP_403_FORBIDDEN: {
                'model': EndpointErrorMessage
                },
            status.HTTP_401_UNAUTHORIZED: {
                'model': EndpointErrorMessage
                }
            }
        )
def create_concept(
        concept_data: ConceptDataPayload,
        response: JSONResponse,
        authorization: str = Header(default="")
        ):
    """Creates a new concept with the given data if valid/available AND authroization is OK"""
    handler = app.endpoint_factory.create_handler(
            'ConceptCreationHandler',
            RegisteredService.CONCEPTS_DS
            )
    handler.receive(
            CreateConcept(
                auth_token=AuthorizationToken(
                    token=authorization,
                    presenter=concept_data.author
                    ),
                **concept_data.dict()
                )
            )
    response.status_code = handler.result.code
    return handler.result.body


@app.post(
        "/links",
        status_code=status.HTTP_201_CREATED,
        responses={
            status.HTTP_201_CREATED: {
                'model': ConceptLinkRecord
                },
            status.HTTP_403_FORBIDDEN: {
                'model': EndpointErrorMessage
                },
            status.HTTP_401_UNAUTHORIZED: {
                'model': EndpointErrorMessage
                }
            }
        )
def create_link(
        link_data: ConceptLinkRecord,
        response: JSONResponse,
        authorization: str = Header(default="")
        ):
    """Creates a link between two concepts in valid and authorization is OK"""
    handler = app.endpoint_factory.create_handler(
            'ConceptLinkingHandler',
            RegisteredService.CONCEPTS_DS
            )
    handler.use_service(RegisteredService.CONCEPTS_DS)
    handler.receive(
            EstablishLink(
                auth_token=AuthorizationToken(
                    token=authorization,
                    presenter=link_data.descendant.split('/')[0]
                    ),
                **link_data.dict()
                )
            )
    response.status_code = handler.result.code
    return handler.result.body


@app.get(
        "/concepts/{author}/{title}",
        responses={
            status.HTTP_200_OK: {
                'model': Union[ConceptFullView, ConceptSimpleView]
                },
            status.HTTP_404_NOT_FOUND: {
                'model': EndpointErrorMessage
                }
            }
        )
def get_specific_concept(
        author: str,
        title: str,
        response: JSONResponse,
        simple: bool = False
        ):
    """Retrieves the concept specified by author/concept if it exists"""
    handler = app.endpoint_factory.create_handler(
            'SpecificConceptRetrievalHandler',
            RegisteredService.CONCEPTS_DS
            )
    handler.use_service(RegisteredService.CONCEPTS_DS)
    handler.receive(
            ConceptRequest(
                title=title,
                author=author,
                simple=simple
                )
            )
    response.status_code = handler.result.code
    return handler.result.body


@app.get(
        "/concepts",
        responses={
            status.HTTP_200_OK: {
                'model': List[ConceptSimpleView]
                }
            }
        )
def search_concepts(
        response: JSONResponse,
        author: str = '',
        title: str = '',
        notbefore: datetime.datetime = None,
        notafter: datetime.datetime = None,
        fuzzy: FuzzyOption = FuzzyOption.NONE
        ):  # pylint:disable=too-many-arguments
    """Retrieves the concepts matching the given criteria"""
    handler = app.endpoint_factory.create_handler(
            'ConceptSearchResultHandler',
            RegisteredService.CONCEPTS_DS
            )
    handler.receive(ConceptSearchQuery(
        author=author,
        title=title,
        not_before=notbefore or datetime.datetime.fromtimestamp(0, datetime.timezone.utc),
        not_after=notafter or datetime.datetime.now(datetime.timezone.utc),
        fuzzy=fuzzy
        ))
    response.status_code = handler.result.code
    return handler.result.body


@app.get(
        "/concepts/{author}/{title}/lineage",
        responses={
            status.HTTP_200_OK: {
                'model': ConceptLineage
                },
            status.HTTP_404_NOT_FOUND: {
                'model': EndpointErrorMessage
                }
            }
        )
def get_lineage(
        author: str,
        title: str,
        response: JSONResponse
        ):
    """Retrieve a tree-like structure showing the lineage of the specified concept"""
    handler = app.endpoint_factory.create_handler(
            'ConceptLineageHandler',
            RegisteredService.CONCEPTS_DS
            )
    handler.receive(ConceptRequest(
        author=author,
        title=title,
        simple=True
        ))
    response.status_code = handler.result.code
    return handler.result.body


@app.post(
        "/accounts/follow",
        status_code=status.HTTP_201_CREATED,
        responses={
            status.HTTP_201_CREATED: {
                'model': EndpointInformationalMessage
                },
            status.HTTP_403_FORBIDDEN: {
                'model': EndpointErrorMessage
                },
            status.HTTP_401_UNAUTHORIZED: {
                'model': EndpointErrorMessage
                }
            }
        )
def start_following(
        response: JSONResponse,
        follow_data: AccountFollowingRecord,
        authorization: str = Header(default='')
        ):
    """Records the event where one account starts following another"""
    handler = app.endpoint_factory.create_handler(
            'StartFollowingAccountHandler',
            RegisteredService.ENGAGE_DS
            )
    handler.receive(FollowRequest(
        auth_token=AuthorizationToken(
            token=authorization,
            presenter=follow_data.follower
            ),
        **follow_data.dict()
        ))
    response.status_code = handler.result.code
    return handler.result.body


@app.get(
        "/accounts/{follower}/follows/{followee}",
        responses={
            status.HTTP_200_OK: {
                'model': EndpointInformationalMessage
                },
            status.HTTP_404_NOT_FOUND: {
                'model': EndpointErrorMessage
                }
            }
        )
def check_following(
        response: JSONResponse,
        follower: str,
        followee: str
        ):
    """Checks if a following record between the specified accounts exists"""
    handler = app.endpoint_factory.create_handler(
            'CheckFollowingStatusHandler',
            RegisteredService.ENGAGE_DS
            )
    handler.receive(AccountFollowingRecord(
        follower=follower,
        followee=followee
        ))
    response.status_code = handler.result.code
    return handler.result.body


@app.delete(
        "/accounts/follow",
        responses={
            status.HTTP_200_OK: {
                'model': EndpointInformationalMessage
                },
            status.HTTP_403_FORBIDDEN: {
                'model': EndpointErrorMessage
                },
            status.HTTP_401_UNAUTHORIZED: {
                'model': EndpointErrorMessage
                }
            }
        )
def stop_following(
        response: JSONResponse,
        follow_data: AccountFollowingRecord,
        authorization: str = Header(default='')
        ):
    """Records the event where one account starts following another"""
    handler = app.endpoint_factory.create_handler(
            'StopFollowingAccountHandler',
            RegisteredService.ENGAGE_DS
            )
    handler.receive(UnfollowRequest(
        auth_token=AuthorizationToken(
            token=authorization,
            presenter=follow_data.follower
            ),
        **follow_data.dict()
        ))
    response.status_code = handler.result.code
    return handler.result.body


@app.post(
        "/accounts/likes",
        status_code=status.HTTP_201_CREATED,
        responses={
            status.HTTP_201_CREATED: {
                'model': EndpointInformationalMessage
                },
            status.HTTP_403_FORBIDDEN: {
                'model': EndpointErrorMessage
                },
            status.HTTP_401_UNAUTHORIZED: {
                'model': EndpointErrorMessage
                }
            }
        )
def start_liking(
        response: JSONResponse,
        like_data: ConceptLikingRecord,
        authorization: str = Header(default='')
        ):
    """Records the event where one user likes a given concept"""
    handler = app.endpoint_factory.create_handler(
            'StartLikingConceptHandler',
            RegisteredService.ENGAGE_DS
            )
    handler.receive(LikeRequest(
        auth_token=AuthorizationToken(
            token=authorization,
            presenter=like_data.user_liking
            ),
        **like_data.dict()
        ))
    response.status_code = handler.result.code
    return handler.result.body


@app.get(
        "/accounts/{display_name}/likes/{concept:path}",
        responses={
            status.HTTP_200_OK: {
                'model': EndpointInformationalMessage
                },
            status.HTTP_404_NOT_FOUND: {
                'model': EndpointErrorMessage
                }
            }
        )
def check_liking(
        response: JSONResponse,
        display_name: str,
        concept: str
        ):
    """Checks if a liking record between the specified account and concept"""
    handler = app.endpoint_factory.create_handler(
            'CheckLikingStatusHandler',
            RegisteredService.ENGAGE_DS
            )
    handler.receive(ConceptLikingRecord(
        user_liking=display_name,
        concept_liked=concept
        ))
    response.status_code = handler.result.code
    return handler.result.body


@app.delete(
        "/accounts/likes",
        responses={
            status.HTTP_200_OK: {
                'model': EndpointInformationalMessage
                },
            status.HTTP_403_FORBIDDEN: {
                'model': EndpointErrorMessage
                },
            status.HTTP_401_UNAUTHORIZED: {
                'model': EndpointErrorMessage
                }
            }
        )
def stop_liking(
        response: JSONResponse,
        like_data: ConceptLikingRecord,
        authorization: str = Header(default='')
        ):
    """Records the event where one account stops liking another"""
    handler = app.endpoint_factory.create_handler(
            'StopLikingConceptHandler',
            RegisteredService.ENGAGE_DS
            )
    handler.receive(UnlikeRequest(
        auth_token=AuthorizationToken(
            token=authorization,
            presenter=like_data.user_liking
            ),
        **like_data.dict()
        ))
    response.status_code = handler.result.code
    return handler.result.body


@app.post(
        "/concepts/{author}/{title}/comment",
        status_code=status.HTTP_201_CREATED,
        responses={
            status.HTTP_201_CREATED: {
                'model': EndpointInformationalMessage
                },
            status.HTTP_403_FORBIDDEN: {
                'model': EndpointErrorMessage
                },
            status.HTTP_401_UNAUTHORIZED: {
                'model': EndpointErrorMessage
                }
            }
        )
def leave_comment_on_concept(
        response: JSONResponse,
        author: str,
        title: str,
        comment_data: ConceptComment,
        authorization: str = Header(default='')
        ):
    """Creates a comment on the concept identified by {author}/{title}"""
    handler = app.endpoint_factory.create_handler(
            'CommentCreationHandler',
            RegisteredService.ENGAGE_DS
            )
    handler.receive(CreateComment(
        auth_token=AuthorizationToken(
            token=authorization,
            presenter=comment_data.comment_author
            ),
        concept_id=f'{author}/{title}',
        response_to=comment_data.comment_id,
        **comment_data.dict()
        ))
    response.status_code = handler.result.code
    return handler.result.body


@app.get(
        "/concepts/{author}/{title}/comment",
        responses={
            status.HTTP_200_OK: {
                'model': EndpointInformationalMessage
                }
            }
        )
def get_comments_section_on_concept(
        response: JSONResponse,
        author: str,
        title: str
        ):
    """Gathers all the comments left on a concept ordered by oldest to newest"""
    handler = app.endpoint_factory.create_handler(
            'ConceptCommentsSectionHandler',
            RegisteredService.ENGAGE_DS
            )
    handler.receive(ConceptRequest(
        author=author,
        title=title,
        simple=True
        ))
    response.status_code = handler.result.code
    return handler.result.body
