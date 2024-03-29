"""
    :module name: s3crud
    :module summary: Base service class for interacting with s3 compatible stores
    :module author: Nathan Mendoza (nathancm@uci.edu)
"""

import logging

import boto3

from ..config import ServiceConfig

LOGGER = logging.getLogger(__name__)


class S3Crud:
    """Class that interfaces with S3 storage provide CRUD operations
    Attributes:
        s3_client: connection to an s3 compatible stores
    """
    LINK_TLL = 300

    def __init__(self):
        self._s3_client = boto3.session.Session().client(
                's3',
                endpoint_url=ServiceConfig.FileBucket.BUCKET_HOST,
                region_name=ServiceConfig.FileBucket.BUCKET_REGION,
                aws_access_key_id=ServiceConfig.FileBucket.BUCKET_KEY,
                aws_secret_access_key=ServiceConfig.FileBucket.BUCKET_SECRET
                )

    def put_item(self, key: str) -> str:
        """Provides a link to put an item in file store bucket with the given key
        Arguments:
            key: unique string that indexes the data. Can be path like
        """
        LOGGER.debug("Generating upload link for %s", key)
        return self._s3_client.generate_presigned_url(
                ClientMethod='put_object',
                Params={
                    'Bucket': ServiceConfig.FileBucket.BUCKET_NAME,
                    'Key': key
                    },
                ExpiresIn=self.LINK_TLL
                )

    def share_item(self, key) -> str:
        """Provide a share link to object with the given key
        Arguments:
            key: string index of the object to share
        Returns:
            [str]: a url to access the object
        """
        LOGGER.debug("Generating share link for object at %s", key)
        return self._s3_client.generate_presigned_url(
                ClientMethod='get_object',
                Params={
                    'Bucket': ServiceConfig.FileBucket.BUCKET_NAME,
                    'Key': key
                    },
                ExpiresIn=self.LINK_TLL
                )
