from django.test import TestCase
from puppies.models import Puppy


class PuppyTest(TestCase):

    def setUp(self):
        Puppy.objects.create(
            name='lucky',
            age=10,
            breed='lab',
            color='white'
        )
        Puppy.objects.create(
            name='blacky',
            age=3,
            breed='doberman',
            color='black'
        )

    def test_puppy_breed(self):
        puppy_lucky = Puppy.objects.get(name='lucky')
        puppy_blacky = Puppy.objects.get(name='blacky')
        self.assertEqual(
            puppy_lucky.get_breed()
        )
        self.assertEqual(
            puppy_blacky.get_breed()
        )
