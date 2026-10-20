from rest_framework import status
from rest_framework.test import APITestCase

from apps.lims.models import Result, ResultStatus, Sample, SampleStatus

PAYLOAD = {"sample_id": "SMP-001", "parameter": "Protein", "value": 12.5, "unit": "%"}


class ResultTestCase(APITestCase):
    def setUp(self):
        self.sample = Sample.objects.create(sample_id="SMP-001", order_id="O", client_id="C")

    def make_result(self, parameter="Protein", sample=None, **kwargs):
        return Result.objects.create(
            sample=sample or self.sample, parameter=parameter, value=1.0, unit="%", **kwargs
        )


class ResultCreateTests(ResultTestCase):
    def test_create_result_is_a_draft(self):
        response = self.client.post("/results", PAYLOAD, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["sample_id"], "SMP-001")
        self.assertEqual(response.data["status"], "draft")
        self.assertEqual(response.data["value"], 12.5)
        self.assertIn("result_id", response.data)
        self.assertEqual(Result.objects.count(), 1)

    def test_client_cannot_create_an_approved_result(self):
        response = self.client.post("/results", {**PAYLOAD, "status": "approved"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "draft")

    def test_unknown_sample_is_rejected(self):
        response = self.client.post("/results", {**PAYLOAD, "sample_id": "NOPE"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["sample_id"][0], "Sample 'NOPE' does not exist.")
        self.assertEqual(Result.objects.count(), 0)

    def test_one_sample_can_have_results_for_many_parameters(self):
        self.client.post("/results", PAYLOAD, format="json")
        response = self.client.post(
            "/results", {**PAYLOAD, "parameter": "Moisture", "value": 8.1}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.sample.results.count(), 2)

    def test_missing_fields_return_field_errors(self):
        response = self.client.post("/results", {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(set(response.data), {"sample_id", "parameter", "value"})

    def test_value_must_be_a_finite_number(self):
        for bad in ("abc", "nan", "inf"):
            with self.subTest(value=bad):
                response = self.client.post("/results", {**PAYLOAD, "value": bad}, format="json")

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("value", response.data)

    def test_unit_is_optional(self):
        payload = {"sample_id": "SMP-001", "parameter": "pH", "value": 7.2}
        response = self.client.post("/results", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["unit"], "")

    def test_results_cannot_be_added_to_closed_samples(self):
        for closed in (SampleStatus.COMPLETED, SampleStatus.CANCELLED):
            with self.subTest(sample_status=closed):
                Sample.objects.filter(pk=self.sample.pk).update(status=closed)
                response = self.client.post("/results", PAYLOAD, format="json")

                self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
                self.assertEqual(Result.objects.count(), 0)


class ResultReadTests(ResultTestCase):
    def setUp(self):
        super().setUp()
        other = Sample.objects.create(sample_id="SMP-002", order_id="O", client_id="C")
        self.make_result("Protein")
        self.make_result("Moisture", status=ResultStatus.APPROVED)
        self.make_result("Protein", sample=other)

    def test_list_results(self):
        response = self.client.get("/results")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 3)

    def test_list_can_be_filtered(self):
        by_sample = self.client.get("/results", {"sample_id": "SMP-001"})
        by_status = self.client.get("/results", {"status": "approved"})
        by_parameter = self.client.get("/results", {"parameter": "Protein"})

        self.assertEqual(by_sample.data["count"], 2)
        self.assertEqual([r["parameter"] for r in by_status.data["results"]], ["Moisture"])
        self.assertEqual(by_parameter.data["count"], 2)

    def test_list_does_not_query_samples_per_row(self):
        with self.assertNumQueries(2):  # one COUNT for pagination + one SELECT with JOIN
            self.client.get("/results")

    def test_results_of_a_sample(self):
        response = self.client.get("/samples/SMP-001/results")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual({r["sample_id"] for r in response.data["results"]}, {"SMP-001"})

    def test_results_of_unknown_sample_return_404(self):
        response = self.client.get("/samples/UNKNOWN/results")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class ResultApproveTests(ResultTestCase):
    def setUp(self):
        super().setUp()
        self.result = self.make_result()

    def approve(self, result_id=None):
        return self.client.patch(f"/results/{result_id or self.result.pk}/approve")

    def test_approve_result(self):
        response = self.approve()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "approved")
        self.result.refresh_from_db()
        self.assertEqual(self.result.status, ResultStatus.APPROVED)

    def test_approving_twice_is_a_conflict(self):
        self.approve()
        response = self.approve()

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_unknown_result_returns_404(self):
        self.assertEqual(self.approve(99999).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.approve("abc").status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_approve_result_of_cancelled_sample(self):
        Sample.objects.filter(pk=self.sample.pk).update(status=SampleStatus.CANCELLED)
        response = self.approve()

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.result.refresh_from_db()
        self.assertEqual(self.result.status, ResultStatus.DRAFT)
