from django.db.models import F
from django.test import TestCase, skipUnlessDBFeature

from .models import Comment, Tenant, User


class CompositePKOrderByTests(TestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.tenant_1 = Tenant.objects.create()
        cls.tenant_2 = Tenant.objects.create()
        cls.tenant_3 = Tenant.objects.create()
        cls.user_1 = User.objects.create(
            tenant=cls.tenant_1,
            id=1,
            email="user0001@example.com",
        )
        cls.user_2 = User.objects.create(
            tenant=cls.tenant_1,
            id=2,
            email="user0002@example.com",
        )
        cls.user_3 = User.objects.create(
            tenant=cls.tenant_2,
            id=3,
            email="user0003@example.com",
        )
        cls.comment_1 = Comment.objects.create(id=1, user=cls.user_1)
        cls.comment_2 = Comment.objects.create(id=2, user=cls.user_1)
        cls.comment_3 = Comment.objects.create(id=3, user=cls.user_2)
        cls.comment_4 = Comment.objects.create(id=4, user=cls.user_3)
        cls.comment_5 = Comment.objects.create(id=5, user=cls.user_1)

    def test_order_comments_by_pk_asc(self):
        self.assertSequenceEqual(
            Comment.objects.order_by("pk"),
            (
                self.comment_1,  # (1, 1)
                self.comment_2,  # (1, 2)
                self.comment_3,  # (1, 3)
                self.comment_5,  # (1, 5)
                self.comment_4,  # (2, 4)
            ),
        )

    def test_order_comments_by_pk_desc(self):
        self.assertSequenceEqual(
            Comment.objects.order_by("-pk"),
            (
                self.comment_4,  # (2, 4)
                self.comment_5,  # (1, 5)
                self.comment_3,  # (1, 3)
                self.comment_2,  # (1, 2)
                self.comment_1,  # (1, 1)
            ),
        )

    def test_order_comments_by_pk_expr(self):
        self.assertQuerySetEqual(
            Comment.objects.order_by("pk"),
            Comment.objects.order_by(F("pk")),
        )
        self.assertQuerySetEqual(
            Comment.objects.order_by("-pk"),
            Comment.objects.order_by(F("pk").desc()),
        )
        self.assertQuerySetEqual(
            Comment.objects.order_by("-pk"),
            Comment.objects.order_by(F("pk").desc(nulls_last=True)),
        )

    def test_order_by_position_of_column_after_composite_pk(self):
        # A composite primary key is selected as one column per target, so
        # ordering by position must account for its width.
        user = User.objects.create(
            tenant=self.tenant_2, id=4, email="user0000@example.com"
        )
        self.assertSequenceEqual(
            User.objects.values_list("pk", "email").order_by("email"),
            (
                (user.pk, "user0000@example.com"),
                (self.user_1.pk, "user0001@example.com"),
                (self.user_2.pk, "user0002@example.com"),
                (self.user_3.pk, "user0003@example.com"),
            ),
        )

    @skipUnlessDBFeature("can_distinct_on_fields")
    def test_distinct_on_field_selected_after_composite_pk(self):
        # DISTINCT ON and ORDER BY must refer to the same physical output
        # position of the field, past the columns the composite primary key
        # spans.
        qs = User.objects.values_list("pk", "email").distinct("email").order_by("email")
        self.assertSequenceEqual(
            qs,
            (
                (self.user_1.pk, "user0001@example.com"),
                (self.user_2.pk, "user0002@example.com"),
                (self.user_3.pk, "user0003@example.com"),
            ),
        )

    def test_union_order_by_composite_pk(self):
        # A composite selection spans several aliased columns in the combined
        # queries, and ordering by it must order by each of them.
        qs = User.objects.values_list("pk", "email")
        self.assertSequenceEqual(
            qs.union(qs).order_by("pk"),
            (
                (self.user_1.pk, self.user_1.email),
                (self.user_2.pk, self.user_2.email),
                (self.user_3.pk, self.user_3.email),
            ),
        )

    def test_union_order_by_field_selected_after_composite_pk(self):
        # Ordering by position must count the physical columns the composite
        # primary key spans in the combined queries.
        user_4 = User.objects.create(
            tenant=self.tenant_2, id=4, email="user0000@example.com"
        )
        qs = User.objects.values_list("pk", "email")
        self.assertSequenceEqual(
            qs.union(qs).order_by("email"),
            (
                (user_4.pk, user_4.email),
                (self.user_1.pk, self.user_1.email),
                (self.user_2.pk, self.user_2.email),
                (self.user_3.pk, self.user_3.email),
            ),
        )
