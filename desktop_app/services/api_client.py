import requests


class ApiClient:
    def __init__(self, base_url: str = "http://localhost:8000", timeout: int = 5) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def get_correlated_events(self, limit: int = 50) -> list:
        try:
            response = requests.get(
                f"{self.base_url}/events/correlated",
                params={"limit": limit},
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, list):
                print("API client error: unexpected response format from backend.")
                return []
            return data
        except requests.RequestException as exc:
            print(f"API client error: unable to reach backend: {exc}")
            return []
        except ValueError:
            print("API client error: invalid JSON response from backend.")
            return []
