from rest_framework import status
from rest_framework.test import APITestCase

from apps.lims.models import Sample, SampleStatus

PAYLOAD = {
    "sample_id": "SMP-001",
    "order_id": "ORD-2026-001",
    "client_id": "CLIENT-001",
}


class SampleCreateTests(APITestCase):
    def test_create_sample_starts_as_registered(self):
        response = self.client.post("/samples", PAYLOAD, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["sample_id"], "SMP-001")
        self.assertEqual(response.data["status"], "registered")
        self.assertEqual(Sample.objects.count(), 1)

    def test_client_cannot_set_initial_status(self):
        response = self.client.post(
            "/samples", {**PAYLOAD, "status": "completed"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "registered")

    def test_duplicate_sample_id_is_rejected(self):
        self.client.post("/samples", PAYLOAD, format="json")
        response = self.client.post("/samples", PAYLOAD, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("sample_id", response.data)
        self.assertEqual(Sample.objects.count(), 1)

    def test_missing_fields_return_field_errors(self):
        response = self.client.post("/samples", {"sample_id": "SMP-002"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(set(response.data), {"order_id", "client_id"})

    def test_blank_sample_id_is_rejected(self):
        response = self.client.post(
            "/samples", {**PAYLOAD, "sample_id": "  "}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("sample_id", response.data)


class SampleReadTests(APITestCase):
    def setUp(self):
        Sample.objects.create(sample_id="SMP-001", order_id="ORD-1", client_id="C-1")
        Sample.objects.create(
            sample_id="SMP-002",
            order_id="ORD-1",
            client_id="C-2",
            status=SampleStatus.IN_PROGRESS,
        )
        Sample.objects.create(sample_id="SMP-003", order_id="ORD-2", client_id="C-1")

    def test_list_returns_all_samples(self):
        response = self.client.get("/samples")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 3)

    def test_list_can_be_filtered(self):
        by_status = self.client.get("/samples", {"status": "in_progress"})
        by_order = self.client.get("/samples", {"order_id": "ORD-1"})
        by_client = self.client.get(
            "/samples", {"client_id": "C-1", "order_id": "ORD-2"}
        )

        self.assertEqual(
            [s["sample_id"] for s in by_status.data["results"]], ["SMP-002"]
        )
        self.assertEqual(by_order.data["count"], 2)
        self.assertEqual(
            [s["sample_id"] for s in by_client.data["results"]], ["SMP-003"]
        )

    def test_retrieve_sample(self):
        response = self.client.get("/samples/SMP-002")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "in_progress")

    def test_retrieve_unknown_sample_returns_404(self):
        response = self.client.get("/samples/UNKNOWN")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class SampleStatusChangeTests(APITestCase):
    def setUp(self):
        self.sample = Sample.objects.create(
            sample_id="SMP-001", order_id="O", client_id="C"
        )

    def patch_status(self, value, sample_id="SMP-001"):
        return self.client.patch(
            f"/samples/{sample_id}/status", {"status": value}, format="json"
        )

    def test_valid_transition_is_saved(self):
        response = self.patch_status("in_progress")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "in_progress")
        self.sample.refresh_from_db()
        self.assertEqual(self.sample.status, SampleStatus.IN_PROGRESS)

    def test_full_happy_path(self):
        self.assertEqual(self.patch_status("in_progress").status_code, 200)
        self.assertEqual(self.patch_status("completed").status_code, 200)

    def test_skipping_a_step_is_a_conflict(self):
        response = self.patch_status("completed")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.sample.refresh_from_db()
        self.assertEqual(self.sample.status, SampleStatus.REGISTERED)

    def test_same_status_is_a_conflict(self):
        response = self.patch_status("registered")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_final_statuses_cannot_be_left(self):
        self.patch_status("cancelled")
        response = self.patch_status("in_progress")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("final", response.data["detail"])

    def test_unknown_status_value_is_a_validation_error(self):
        response = self.patch_status("finished")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("status", response.data)

    def test_missing_status_is_a_validation_error(self):
        response = self.client.patch("/samples/SMP-001/status", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("status", response.data)

    def test_unknown_sample_returns_404(self):
        response = self.patch_status("in_progress", sample_id="UNKNOWN")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
