import logging
from typing import Any

import requests

from .config import get_settings

logger = logging.getLogger(__name__)


def create_api_client() -> "MarvinAPIClient":
    """Create API client with settings."""
    settings = get_settings()
    return MarvinAPIClient(
        api_key=settings.amazing_marvin_api_key,
        full_access_token=settings.amazing_marvin_full_access_token,
    )


class MarvinAPIClient:
    """API client for Amazing Marvin"""

    def __init__(self, api_key: str, full_access_token: str = ""):
        """
        Initialize the API client with API keys

        Args:
            api_key: Amazing Marvin API key (standard operations)
            full_access_token: Full-access token for update/delete/get-by-id operations
        """
        self.api_key = api_key
        self.full_access_token = full_access_token
        self.base_url = "https://serv.amazingmarvin.com/api"  # Removed v1 from URL
        self.headers = {"X-API-Token": api_key}
        self.full_access_headers = {"X-Full-Access-Token": full_access_token}

    def _require_full_access(self) -> None:
        """Raise an error if the full-access token is not configured."""
        if not self.full_access_token:
            raise ValueError(
                "Full-access token not configured. Set AMAZING_MARVIN_FULL_ACCESS_TOKEN environment variable."
            )

    def _make_full_access_request(
        self, method: str, endpoint: str, data: dict | None = None
    ) -> Any:
        """Make a request using the full-access token."""
        self._require_full_access()
        url = f"{self.base_url}{endpoint}"
        logger.debug("Making full-access %s request to %s", method, url)

        try:
            if method.lower() == "get":
                response = requests.get(url, headers=self.full_access_headers)
            elif method.lower() == "post":
                response = requests.post(
                    url, headers=self.full_access_headers, json=data
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()

            no_content_status = 204
            if response.status_code == no_content_status or not response.content:
                return {}

            return response.json()
        except requests.exceptions.HTTPError:
            logger.exception("HTTP error (full-access)")
            raise
        except requests.exceptions.RequestException:
            logger.exception("Request error (full-access)")
            raise

    def _make_request(
        self, method: str, endpoint: str, data: dict | None = None
    ) -> Any:
        """Make a request to the API"""
        url = f"{self.base_url}{endpoint}"
        logger.debug("Making %s request to %s", method, url)

        try:
            if method.lower() == "get":
                response = requests.get(url, headers=self.headers)
            elif method.lower() == "post":
                response = requests.post(url, headers=self.headers, json=data)
            elif method.lower() == "put":
                response = requests.put(url, headers=self.headers, json=data)
            elif method.lower() == "delete":
                response = requests.delete(url, headers=self.headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()

            # Handle 204 No Content responses
            no_content_status = 204
            if response.status_code == no_content_status or not response.content:
                return {}

            return response.json()
        except requests.exceptions.HTTPError:
            logger.exception("HTTP error")
            raise
        except requests.exceptions.RequestException:
            logger.exception("Request error")
            raise

    def get_tasks(self, date: str | None = None) -> list[dict]:
        """Get all tasks and projects (use /todayItems or /dueItems for scheduled/due, or /children for subtasks)"""
        # The Marvin API does not provide a /tasks endpoint. Use /todayItems for scheduled items, /dueItems for due, or /children for subtasks.
        endpoint = "/todayItems"
        if date:
            endpoint += f"?date={date}"
        return self._make_request("get", endpoint)

    def get_task(self, task_id: str) -> dict:
        """Get a specific task or project by ID (requires full-access token)."""
        return self._make_full_access_request("get", f"/doc?id={task_id}")

    def get_projects(self) -> list[dict]:
        """
        Get all projects (as categories with type 'project').

        Note: "Work" and "Personal" are default projects created for most users.
        """
        categories = self.get_categories()
        return [cat for cat in categories if cat.get("type") == "project"]

    def get_categories(self) -> list[dict]:
        """Get all categories"""
        return self._make_request("get", "/categories")

    def get_labels(self) -> list[dict]:
        """Get all labels"""
        return self._make_request("get", "/labels")

    def get_due_items(self) -> list[dict]:
        """Get all due items (experimental endpoint)"""
        return self._make_request("get", "/dueItems")

    def get_done_items(self, date: str | None = None) -> list[dict]:
        """Get completed/done items, optionally filtered by completion date

        Args:
            date: Optional date in YYYY-MM-DD format to filter by completion date.
                 If not provided, defaults to today's completed items.

        Returns:
            List of completed items, filtered by completion date if specified
        """
        endpoint = "/doneItems"
        if date:
            endpoint += f"?date={date}"
        return self._make_request("get", endpoint)

    def get_all_tasks_for_date(self, date: str) -> list[dict]:
        """Get all tasks for a specific date, including completed ones.

        Args:
            date: Date in YYYY-MM-DD format

        Returns:
            List of tasks for that date (both completed and pending)
        """
        try:
            # Try different approaches to get completed tasks
            result = []

            # 1. Try todayItems with date parameter
            today_items = self._make_request("get", f"/todayItems?date={date}")
            result.extend(today_items)

            # 2. Try any additional endpoints that might have completed tasks
            # The API might have other ways to access completed items
        except Exception as e:
            logger.warning("Could not get tasks for date %s: %s", date, e)
            return []
        else:
            return result

    def get_children(self, parent_id: str) -> list[dict]:
        """Get child tasks of a specific parent task or project (experimental endpoint)"""
        try:
            return self._make_request("get", f"/children?parentId={parent_id}")
        except requests.exceptions.HTTPError as e:
            not_found_status = 404
            if e.response.status_code == not_found_status:
                logger.warning(
                    "Children endpoint not available for parent %s", parent_id
                )
                return []
            raise

    def create_task(self, task_data: dict) -> dict:
        """Create a new task (uses /addTask endpoint)"""
        return self._make_request("post", "/addTask", data=task_data)

    def mark_task_done(self, item_id: str, timezone_offset: int = 0) -> dict:
        """Mark a task as done (experimental endpoint)"""
        return self._make_request(
            "post",
            "/markDone",
            data={"itemId": item_id, "timeZoneOffset": timezone_offset},
        )

    def test_api_connection(self) -> str:
        """Test API connection and credentials"""
        url = f"{self.base_url}/test"
        try:
            response = requests.post(url, headers=self.headers)
            response.raise_for_status()
            return response.text.strip()  # Returns "OK" as plain text
        except requests.exceptions.RequestException:
            logger.exception("API connection test failed")
            raise

    def start_time_tracking(self, task_id: str) -> dict:
        """Start time tracking for a task (experimental endpoint)"""
        return self._make_request(
            "post", "/track", data={"taskId": task_id, "action": "START"}
        )

    def stop_time_tracking(self, task_id: str) -> dict:
        """Stop time tracking for a task (experimental endpoint)"""
        return self._make_request(
            "post", "/track", data={"taskId": task_id, "action": "STOP"}
        )

    def get_time_tracks(self, task_ids: list[str]) -> dict:
        """Get time tracking data for specific tasks (experimental endpoint)"""
        return self._make_request("post", "/tracks", data={"taskIds": task_ids})

    def claim_reward_points(self, points: int, item_id: str, date: str) -> dict:
        """Claim reward points for completing a task"""
        return self._make_request(
            "post",
            "/claimRewardPoints",
            data={"points": points, "itemId": item_id, "date": date},
        )

    def get_kudos_info(self) -> dict:
        """Get kudos information"""
        return self._make_request("get", "/kudos")

    def get_goals(self) -> list[dict]:
        """Get all goals"""
        return self._make_request("get", "/goals")

    def get_account_info(self) -> dict:
        """Get account information"""
        return self._make_request("get", "/me")

    def get_currently_tracked_item(self) -> dict:
        """Get currently tracked item"""
        result = self._make_request("get", "/trackedItem")
        if not result:
            return {"message": "No item currently being tracked"}
        return result

    def create_project(self, project_data: dict) -> dict:
        """Create a new project (experimental endpoint)"""
        return self._make_request("post", "/addProject", data=project_data)

    def update_task(self, task_id: str, setters: list[dict]) -> dict:
        """Update a task's fields (requires full-access token).

        Args:
            task_id: The document ID to update.
            setters: List of {"key": field_path, "val": new_value} dicts.
        """
        return self._make_full_access_request(
            "post", "/doc/update", data={"itemId": task_id, "setters": setters}
        )

    def delete_task(self, task_id: str) -> dict:
        """Permanently delete a task (requires full-access token).

        Warning: This bypasses Marvin's trash. Deletion is not recoverable
        through the Marvin UI. Prefer using update_task to set deletedAt
        for recoverable trash behavior.
        """
        return self._make_full_access_request(
            "post", "/doc/delete", data={"itemId": task_id}
        )
