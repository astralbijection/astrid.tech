from blog.models import SyndicationTarget


# noinspection PyAttributeOutsideInit
class SyndicationTestMixin:
    def set_up_syndication_targets(self):
        self.syn_target_1 = SyndicationTarget.objects.create(
            id='https://example@twitter.com',
            name='My cool twitter'
        )
        self.syn_target_2 = SyndicationTarget.objects.create(
            id='https://username@some.mastodon.server',
            name='My cooler mastodon'
        )
        self.syn_target_3 = SyndicationTarget.objects.create(
            id='https://mycool.tumblr.com',
            name='A tumblr site'
        )
        self.disabled_syn_target = SyndicationTarget.objects.create(
            id='https://not_my@twitter.com',
            name='My uncool twitter',
            enabled=False
        )
