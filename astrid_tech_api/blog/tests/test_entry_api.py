from datetime import datetime

import pytz
from freezegun import freeze_time
from rest_framework.test import APITestCase

from blog.models import Entry, Tag, Syndication
from .utils import SyndicationTestMixin

create_on = datetime(2021, 6, 18, 5, 5, tzinfo=pytz.utc)
retrieve_on = datetime(2021, 6, 18, 5, 6, tzinfo=pytz.utc)


class EntryRetrieveAPI(APITestCase, SyndicationTestMixin):
    @freeze_time(create_on)
    def setUp(self):
        self.set_up_syndication_targets()

        self.entries = [
            Entry.objects.create(
                slug_name=f'entry-{i}',
                title=f'Entry #{i}',
                ordinal=i
            )
            for i in range(20)
        ]

        self.prime_tag = Tag.objects.create(id='prime')
        self.even_tag = Tag.objects.create(id='even')

        for i in [2, 3, 5, 7]:
            self.entries[i].tags.add(self.prime_tag)

        for i in [2, 4, 6, 8]:
            self.entries[i].tags.add(self.even_tag)

        # Syndication testing
        self.syn_16_1 = Syndication.objects.create(
            entry=self.entries[16],
            target=self.syn_target_1,
            status=Syndication.Status.ERROR,
        )
        self.syn_16_2 = Syndication.objects.create(
            entry=self.entries[16],
            target=self.syn_target_2,
            location='https://somewhere.example.com/over/the/rainbow',
            status=Syndication.Status.SYNDICATED,
        )
        self.syn_16_3 = Syndication.objects.create(
            entry=self.entries[16],
            target=self.syn_target_3,
            status=Syndication.Status.SCHEDULED,
        )

    @freeze_time(retrieve_on)
    def test_root_returns_posts(self):
        response = self.client.get('/api/entries/')

        self.assertEqual(20, len(response.json()))

    @freeze_time(retrieve_on)
    def test_can_filter_ordinals(self):
        response = self.client.get('/api/entries/', {'ordinal': 4})

        [obj] = response.json()
        self.assertEqual('Entry #4', obj['title'])

    @freeze_time(retrieve_on)
    def test_tag_filter_is_and(self):
        response = self.client.get('/api/entries/?has_tag=even&has_tag=prime')

        [obj] = response.json()
        self.assertEqual('Entry #2', obj['title'])

    @freeze_time(retrieve_on)
    def test_retrieves_by_uuid(self):
        response = self.client.get(f'/api/entries/{self.entries[2].uuid}/')

        self.assertEqual(200, response.status_code, msg=response.content)
        obj = response.json()
        self.assertEqual('Entry #2', obj['title'])
        self.assertCountEqual(['even', 'prime'], obj['tags'])

    @freeze_time(retrieve_on)
    def test_retrieves_only_successful_syndications(self):
        response = self.client.get(f'/api/entries/{self.entries[16].uuid}/')

        self.assertEqual(200, response.status_code, msg=response.content)
        obj = response.json()
        [only_syn] = obj['syndications']
        self.assertEqual(self.syn_16_2.location, only_syn['location'])
