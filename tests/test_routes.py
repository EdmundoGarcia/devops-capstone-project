"""
Account API Service Test Suite

Test cases can be run with the following:
  nosetests -v --with-spec --spec-color
  coverage report -m
"""
import os
import logging
from unittest import TestCase
from service.common import status  # HTTP Status Codes
from service.models import db, Account, init_db
from service import app, talisman
from tests.factories import AccountFactory

DATABASE_URI = os.getenv(
    "DATABASE_URI", "postgresql://postgres:postgres@localhost:5432/postgres"
)

BASE_URL = "/accounts"
HTTPS_ENVIRON = {"wsgi.url_scheme": "https"}


######################################################################
#  T E S T   C A S E S
######################################################################
class TestAccountService(TestCase):
    """Account Service Tests"""

    @classmethod
    def setUpClass(cls):
        """Run once before all tests"""
        app.config["TESTING"] = True
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URI
        # pylint: disable=no-member
        app.logger.setLevel(logging.CRITICAL)
        # pylint: enable=no-member
        init_db(app)
        talisman.force_https = False

    @classmethod
    def tearDownClass(cls):
        """Runs once before test suite"""

    def setUp(self):
        """Runs before each test"""
        # pylint: disable=no-member
        db.session.query(Account).delete()  # clean up the last tests
        db.session.commit()
        # pylint: enable=no-member

        self.client = app.test_client()

    def tearDown(self):
        """Runs once after each test case"""
        # pylint: disable=no-member
        db.session.remove()
        # pylint: enable=no-member

    ######################################################################
    #  H E L P E R   M E T H O D S
    ######################################################################

    def _create_accounts(self, count):
        """Factory method to create accounts in bulk"""
        accounts = []
        for _ in range(count):
            account = AccountFactory()
            # pylint: disable=no-member
            payload = account.serialize()
            # pylint: enable=no-member
            response = self.client.post(BASE_URL, json=payload)
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                "Could not create test Account",
            )
            new_account = response.get_json()
            account.id = new_account["id"]
            accounts.append(account)
        return accounts

    ######################################################################
    #  A C C O U N T   T E S T   C A S E S
    ######################################################################

    def test_index(self):
        """It should get 200_OK from the Home Page"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_health(self):
        """It should be healthy"""
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "OK")

    def test_create_account(self):
        """It should Create a new Account"""
        account = AccountFactory()
        # pylint: disable=no-member
        payload = account.serialize()
        # pylint: enable=no-member
        response = self.client.post(
            BASE_URL, json=payload, content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Make sure location header is set
        location = response.headers.get("Location", None)
        self.assertIsNotNone(location)

        # Check the data is correct
        new_account = response.get_json()
        self.assertEqual(new_account["name"], account.name)
        self.assertEqual(new_account["email"], account.email)
        self.assertEqual(new_account["address"], account.address)
        self.assertEqual(new_account["phone_number"], account.phone_number)
        self.assertEqual(new_account["date_joined"], str(account.date_joined))

    def test_bad_request(self):
        """It should not Create an Account when sending the wrong data"""
        response = self.client.post(BASE_URL, json={"name": "not enough data"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unsupported_media_type(self):
        """It should not Create an Account when sending the wrong media type"""
        account = AccountFactory()
        # pylint: disable=no-member
        payload = account.serialize()
        # pylint: enable=no-member
        response = self.client.post(BASE_URL, json=payload, content_type="test/html")
        self.assertEqual(response.status_code, status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

    def test_read_an_account(self):
        """This test should read a single account and return 200_OK"""
        account = self._create_accounts(1)[0]
        resp = self.client.get(
            f"{BASE_URL}/{account.id}", content_type="application/json"
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(data["name"], account.name)

    def test_account_not_found(self):
        """It should not read an account if it is not found"""
        resp = self.client.get(f"{BASE_URL}/0")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_account_list(self):
        """It should return a list of all of the accounts"""
        self._create_accounts(5)
        resp = self.client.get(BASE_URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.get_json()
        self.assertEqual(len(data), 5)

    def test_update_account(self):
        """It should update an existing account"""
        test_account = AccountFactory()
        # pylint: disable=no-member
        payload = test_account.serialize()
        # pylint: enable=no-member
        resp = self.client.post(BASE_URL, json=payload)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        new_account = resp.get_json()
        new_account["name"] = "John Doe"
        resp = self.client.put(f"{BASE_URL}/{new_account['id']}", json=new_account)
        updated_account = resp.get_json()
        self.assertEqual(updated_account["name"], "John Doe")

    def test_delete_account(self):
        """It should delete an account"""
        account = self._create_accounts(1)[0]
        resp = self.client.delete(f"{BASE_URL}/{account.id}")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    def test_method_not_allowed(self):
        """It should not allow calling an endpoint with the wrong method call"""
        resp = self.client.delete(BASE_URL)
        self.assertEqual(resp.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_security_headers(self):
        """It should return the security headers"""
        resp = self.client.get("/", environ_overrides=HTTPS_ENVIRON)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        headers = {
            "X-Frame-Options": "SAMEORIGIN",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'self'; object-src 'none'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }
        for key, value in headers.items():
            self.assertEqual(resp.headers.get(key), value)

    def test_cors(self):
        """It should return a CORS header"""
        resp = self.client.get("/", environ_overrides=HTTPS_ENVIRON)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        self.assertEqual(resp.headers.get("Access-Control-Allow-Origin"), "*")
