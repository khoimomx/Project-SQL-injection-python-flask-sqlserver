"""HTTP integration tests against an initialized, real SQL Server lab database."""

import time
import unittest
import uuid
from urllib.parse import quote

import pyodbc

import database
from app import app
from lessons import BY_NUMBER, LESSONS


def probe(client, number, value, *, fixed=False):
    lesson = BY_NUMBER[number]
    path = f"/lab/{number}"
    query = {"mode": "fixed"} if fixed else {}
    if lesson.source == "url":
        return client.get(path, query_string={**query, lesson.key: value})
    if lesson.source == "header":
        return client.post(path, query_string=query, headers={lesson.key: value})
    if lesson.source == "cookie":
        client.set_cookie(lesson.key, quote(value, safe=""), path=path)
        return client.get(path, query_string=query)
    return client.post(path, data={lesson.key: value}, query_string=query)


class LabTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_catalogue_and_http_contract(self):
        for path in ("/", "/guide", *(f"/lessons/{lab.number}" for lab in LESSONS)):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)
        self.assertEqual(self.client.post("/lab/1").status_code, 405)
        self.assertEqual(self.client.get("/lab/2?q=x").status_code, 405)
        self.assertEqual(self.client.get("/lab/1").status_code, 400)
        self.assertEqual(self.client.get("/lab/1?id=1&mode=other").status_code, 400)
        self.assertEqual(self.client.get("/lab/100").status_code, 404)

    def test_normal_requests_work_in_both_modes(self):
        for lesson in LESSONS[:-1]:
            with self.subTest(number=lesson.number):
                normal = probe(self.client, lesson.number, lesson.baseline)
                fixed = probe(self.client, lesson.number, lesson.baseline, fixed=True)
                self.assertEqual(normal.status_code, 200, normal.text)
                self.assertEqual(fixed.status_code, 200, fixed.text)
                self.assertEqual(normal.data, fixed.data)

    def test_in_band_codes_only_appear_in_vulnerable_mode(self):
        cases = {1: "ATLAS-17", 2: "ORBIT-23", 3: "DELTA-41", 4: "ION-62",
                 9: "RADIO-18", 10: "EMBER-20"}
        for number, code in cases.items():
            value = BY_NUMBER[number].probes[-1][1]
            with self.subTest(number=number):
                normal = probe(self.client, number, value)
                self.assertEqual(normal.status_code, 422 if number in (3, 4, 9) else 200, normal.text)
                self.assertIn(code, normal.text)
                fixed = probe(self.client, number, value, fixed=True)
                self.assertEqual(fixed.status_code, 200, fixed.text)
                self.assertNotIn(code, fixed.text)

    def test_header_falls_back_to_real_user_agent(self):
        payload = BY_NUMBER[9].probes[-1][1]
        res = self.client.post("/lab/9", headers={"User-Agent": payload})
        self.assertIn("RADIO-18", res.text)
        res = self.client.post("/lab/9?mode=fixed", headers={"User-Agent": payload})
        self.assertEqual(res.status_code, 200)
        self.assertNotIn("RADIO-18", res.text)

    def test_boolean_oracles_have_two_signals(self):
        for number in (5, 6):
            with self.subTest(number=number):
                false, true = [value for _, value in BY_NUMBER[number].probes]
                hit = probe(self.client, number, true)
                miss = probe(self.client, number, false)
                self.assertEqual(hit.data, probe(self.client, number, BY_NUMBER[number].baseline).data)
                self.assertNotEqual(hit.data, miss.data)
                self.assertEqual(probe(self.client, number, true, fixed=True).data, miss.data)
                self.assertEqual(hit.status_code, 200)
                self.assertEqual(miss.status_code, 200)

    def test_timing_is_measured_at_the_sql_batch_boundary(self):
        for number in (7, 8):
            with self.subTest(number=number):
                false, true = [value for _, value in BY_NUMBER[number].probes]
                durations = []
                for value, fixed in ((false, False), (true, False), (true, True)):
                    start = time.monotonic()
                    res = probe(self.client, number, value, fixed=fixed)
                    durations.append(time.monotonic() - start)
                    self.assertEqual(res.status_code, 200)
                    self.assertEqual(res.text, "Đã nhận yêu cầu.")
                self.assertGreater(durations[1] - min(durations[0], durations[2]), 1.4, durations)
                self.assertLess(durations[2], durations[1] - 1.2, durations)

    def test_update_is_per_learner_and_mode(self):
        value = BY_NUMBER[11].probes[-1][1]
        self.assertIn("badge = Mentor", probe(self.client, 11, value).text)
        fixed = probe(self.client, 11, value, fixed=True)
        self.assertIn(value, fixed.text)
        self.assertIn("badge = Member", fixed.text)
        self.assertIn("badge = Member", probe(app.test_client(), 11, "Mai").text)

    def test_second_order_needs_two_requests_and_the_same_session(self):
        payload = BY_NUMBER[12].probes[-1][1]
        self.assertEqual(self.client.post("/lab/12").status_code, 409)
        for suffix in ("", "?mode=fixed"):
            saved = self.client.post("/lab/12/save" + suffix, data={"filter": payload})
            self.assertEqual(saved.status_code, 200, saved.text)
            self.assertNotIn("ECHO-24", saved.text)
            # A new value in the second request cannot override the stored one.
            res = self.client.post("/lab/12" + suffix, data={"filter": "MK-01"})
            self.assertEqual(res.status_code, 200)
            self.assertEqual("ECHO-24" in res.text, suffix == "")
        self.assertEqual(app.test_client().post("/lab/12").status_code, 409)
        self.client.post("/lab/12/save?mode=fixed", data={"filter": "MK-01"})
        self.assertIn("Sổ tay lưới", self.client.post("/lab/12?mode=fixed").text)

    def test_runtime_identity_permissions_and_scope(self):
        scope = uuid.uuid4().hex + "v"
        with database.training_connection(scope) as db:
            cur = db.cursor()
            self.assertEqual(cur.execute("SELECT USER_NAME()").fetchval(), "lab_student")
            self.assertEqual(cur.execute("SELECT HAS_PERMS_BY_NAME(DB_NAME(),'DATABASE','CONTROL')").fetchval(), 0)
            self.assertEqual(cur.execute("SELECT HAS_PERMS_BY_NAME('dbo.catalog','OBJECT','UPDATE')").fetchval(), 0)
            cur.execute("INSERT dbo.saved_filters(scope, term) VALUES (?, 'my filter')", scope)
        with database.training_connection(uuid.uuid4().hex + "v") as db:
            self.assertEqual(db.cursor().execute("SELECT COUNT(*) FROM dbo.saved_filters WHERE scope=?", scope).fetchval(), 0)
        try:
            with database.training_connection(scope) as db:
                db.cursor().execute("REVERT")
                self.assertEqual(db.cursor().execute("SELECT USER_NAME()").fetchval(), "lab_student")
        except pyodbc.ProgrammingError:
            pass  # SQL Server may reject REVERT outright.


if __name__ == "__main__":
    unittest.main()
