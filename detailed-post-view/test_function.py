"""
    :module_name: test_function
    :module_summary: testing detailed-post-view handler function
    :module_author: Utsav Sampat
"""

import json
import unittest
from function import handler
from ideadb_handler import *

MOCK_POST_OBJ = {
    "IdeaPostID": {"S": "1"},
    "IdeaAuthorID": {"S":"testauthor"},
    "contributors": {"SS":["testcontributor1", "testcontributor2"]},
    "title": {"S": "Jetpack"},
    "description": {"S": "This is my idea for a"},
    "media_links": {"SS": ["http://dummyimage.com/400x600.png/dddddd/000000"]}
}

MOCK_POST = {key:list(obj.values())[0] for key,obj in MOCK_POST_OBJ.items()}

class DetailedPostViewTests(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(DetailedPostViewTests, self).__init__(*args, **kwargs)
        self.posts = IdeaPostTable()
        self.posts.add_post(MOCK_POST_OBJ)

    def test_get_nonexisting_post(self):
        response = handler({'body': {'IdeaPostID': '100', 'IdeaAuthorID': '100'}}, {})
        self.assertEqual(
            json.loads(response['body']), {}, 
            'body should be empty if post does not exist'
        )
        
    def test_get_existing_post(self):
        response = handler(
            event = {'body': {
                'IdeaPostID': MOCK_POST['IdeaPostID'], 
                'IdeaAuthorID': MOCK_POST['IdeaAuthorID']
            }},
            context = {}
        )
        response_body = json.loads(response['body'])
        self.assertNotEqual(
            response_body, {},
            'body should not be empty if post is found'
        )

    def test_post_fields(self):
        response = handler(
            event = {'body': {
                'IdeaPostID': MOCK_POST['IdeaPostID'], 
                'IdeaAuthorID': MOCK_POST['IdeaAuthorID']
            }},
            context = {}
        )
        response_body = json.loads(response['body'])
        
        for mock_post_key in MOCK_POST.keys():
            self.assertIn(
                mock_post_key, response_body, 
                f'{mock_post_key} does not exist in returned post'
            )
        
        self.assertEqual(
            # adding one for 'created_at' field
            len(response_body), len(MOCK_POST.keys())+1,
            'Number of keys in response does not match'
        )

    def test_post_content(self):
        response = handler(
            event = {'body': {
                'IdeaPostID': MOCK_POST['IdeaPostID'], 
                'IdeaAuthorID': MOCK_POST['IdeaAuthorID']
            }},
            context = {}
        )
        response_body = json.loads(response['body'])
        for post_key, post_value in response_body.items():
            self.assertEqual(
                post_value, MOCK_POST_OBJ[post_key],
                f'{post_key}\'s value should have been {MOCK_POST_OBJ[post_key]} instade of {post_value}'
            )

    def test_statuscode_200(self):
        response = handler(
            event = {'body': {
                'IdeaPostID': MOCK_POST['IdeaPostID'], 
                'IdeaAuthorID': MOCK_POST['IdeaAuthorID']
            }},
            context = {}
        )
        self.assertEqual(
            response['statusCode'], 200,
            f'statusCode should be 200 instade of {response["statusCode"]}'
        )

    def test_statuscode_400(self):
        response = handler(
            event = {'body': {}},
            context = {}
        )
        self.assertEqual(
            response['statusCode'], 400,
            f'statusCode should be 400 instade of {response["statusCode"]}'
        )

    
if __name__ == '__main__':
    unittest.main()