from rest_framework import status
from rest_framework.test import APITestCase

from apps.lims.models import Result, ResultStatus, Sample, SampleStatus


class ExportTests(APITestCase):
    def setUp(self):
        self.sample = Sample.objects.create(
            sample_id="SMP-001",
            order_id="ORD-2026-001",
            client_id="CLIENT-001",
            status=SampleStatus.COMPLETED,
        )

    def add_result(self, parameter, value, result_status, sample=None, unit="%"):
        return Result.objects.create(
            sample=sample or self.sample,
            parameter=parameter,
            value=value,
            unit=unit,
            status=result_status,
        )

    def export(self, sample_id="SMP-001"):
        return self.client.get(f"/integration/export/{sample_id}")

    def test_export_matches_the_agreed_structure(self):
        self.add_result("Protein", 12.5, ResultStatus.APPROVED)

        response = self.export()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "sample_id": "SMP-001",
                "order_id": "ORD-2026-001",
                "client_id": "CLIENT-001",
                "sample_status": "completed",
                "results": [
                    {
                        "parameter": "Protein",
                        "value": 12.5,
                        "unit": "%",
                        "status": "approved",
                    }
                ],
            },
        )

    def test_only_approved_results_are_exported(self):
        self.add_result("Protein", 12.5, ResultStatus.APPROVED)
        self.add_result("Moisture", 8.1, ResultStatus.DRAFT)
        self.add_result("pH", 7.0, ResultStatus.APPROVED, unit="")

        results = self.export().json()["results"]

        self.assertEqual([r["parameter"] for r in results], ["Protein", "pH"])
        self.assertTrue(all(r["status"] == "approved" for r in results))

    def test_sample_without_approved_results_has_an_empty_list(self):
        self.add_result("Protein", 12.5, ResultStatus.DRAFT)

        response = self.export()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["results"], [])

    def test_results_of_other_samples_are_not_exported(self):
        other = Sample.objects.create(sample_id="SMP-002", order_id="O", client_id="C")
        self.add_result("Protein", 12.5, ResultStatus.APPROVED)
        self.add_result("Fat", 3.3, ResultStatus.APPROVED, sample=other)

        results = self.export().json()["results"]

        self.assertEqual([r["parameter"] for r in results], ["Protein"])

    def test_unknown_sample_returns_404(self):
        self.assertEqual(self.export("UNKNOWN").status_code, status.HTTP_404_NOT_FOUND)

    def test_export_uses_two_queries_regardless_of_result_count(self):
        for i in range(5):
            self.add_result(f"P{i}", i, ResultStatus.APPROVED)

        with self.assertNumQueries(2):  # the sample + approved results
            self.export()


class ExportConsistencyTests(APITestCase):
    """Walks through the whole workflow via the API and checks the export at each point."""

    def post(self, url, data):
        return self.client.post(url, data, format="json")

    def patch(self, url, data=None):
        return self.client.patch(url, data, format="json")

    def test_export_follows_approvals_and_sample_status(self):
        self.post(
            "/samples", {"sample_id": "SMP-001", "order_id": "O-1", "client_id": "C-1"}
        )
        self.patch("/samples/SMP-001/status", {"status": "in_progress"})
        protein = self.post(
            "/results",
            {
                "sample_id": "SMP-001",
                "parameter": "Protein",
                "value": 12.5,
                "unit": "%",
            },
        ).data["result_id"]
        self.post(
            "/results",
            {
                "sample_id": "SMP-001",
                "parameter": "Moisture",
                "value": 8.1,
                "unit": "%",
            },
        )

        export = self.client.get("/integration/export/SMP-001").json()
        self.assertEqual(export["sample_status"], "in_progress")
        self.assertEqual(export["results"], [])

        self.patch(f"/results/{protein}/approve")
        self.patch("/samples/SMP-001/status", {"status": "completed"})

        export = self.client.get("/integration/export/SMP-001").json()
        self.assertEqual(export["sample_status"], "completed")
        self.assertEqual([r["parameter"] for r in export["results"]], ["Protein"])
