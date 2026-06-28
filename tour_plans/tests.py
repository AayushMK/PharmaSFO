from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Area, TourPlan


class TourPlanBulkSaveTests(TestCase):
    def test_bulk_save_creates_tour_plans(self):
        user = get_user_model().objects.create_user(username="tester", password="secret123")
        area = Area.objects.create(name="Test Area")

        self.client.force_login(user)
        response = self.client.post(
            reverse("add_tour_plan"),
            {
                "entries": '[{"plan_date":"2026-07-01","area":"' + str(area.pk) + '","worked_with":"","remarks":"Test remarks"}]',
            },
        )

        self.assertRedirects(response, reverse("tour_plans"))
        self.assertEqual(TourPlan.objects.count(), 1)
