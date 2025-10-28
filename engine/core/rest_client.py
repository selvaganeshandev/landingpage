import base64
import json
from http.client import HTTPSConnection
from typing import Dict, List, Any, Optional


class RestClient:
    """
    REST API client for DataForSEO API
    """
    domain = "api.dataforseo.com"

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password

    def request(self, path: str, method: str, data: Optional[str] = None) -> Dict[str, Any]:
        """
        Make a request to the DataForSEO API
        """
        connection = HTTPSConnection(self.domain)
        try:
            base64_bytes = base64.b64encode(
                ("%s:%s" % (self.username, self.password)).encode("ascii")
            ).decode("ascii")
            headers = {
                'Authorization': 'Basic %s' % base64_bytes,
                'Content-Encoding': 'gzip',
                'Content-Type': 'application/json'
            }
            connection.request(method, path, headers=headers, body=data)
            response = connection.getresponse()
            return json.loads(response.read().decode())
        finally:
            connection.close()

    def get(self, path: str) -> Dict[str, Any]:
        """
        Make a GET request
        """
        return self.request(path, 'GET')

    def post(self, path: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make a POST request
        """
        if isinstance(data, str):
            data_str = data
        else:
            data_str = json.dumps(data)
        return self.request(path, 'POST', data_str)


class DataForSEOClient:
    """
    Specialized client for DataForSEO keyword scraping
    """
    
    def __init__(self, username: str, password: str):
        self.client = RestClient(username, password)
    
    def scrape_target_domain(self, domain_name: str, limit: int = 50) -> List[str]:
        """
        Scrape keywords for a target domain using DataForSEO API
        
        Args:
            domain_name: The domain to scrape keywords for
            limit: Maximum number of keywords to retrieve (default: 50)
            
        Returns:
            List of keywords found for the domain
        """
        target_domain_keywords = []
        
        # Prepare the request data
        client_post_data = {
            0: {
                "target": domain_name,
                "load_rank_absolute": False,
                "order_by": ["ranked_serp_element.serp_item.rank_group,asc"],
                "limit": limit,
                "offset": 0
            }
        }
        
        # Make the API request
        scrap_target_domain_slug = "/v3/dataforseo_labs/google/ranked_keywords/live"
        response = self.client.post(scrap_target_domain_slug, client_post_data)
        
        if 'status_code' in response:
            if response["status_code"] == 20000:
                try:
                    if isinstance(response['tasks'][0]['result'], list):
                        if isinstance(response['tasks'][0]['result'][0]['items'], list):
                            for resp_set in response['tasks'][0]['result'][0]['items']:
                                if 'keyword_data' in resp_set:
                                    if 'keyword' in resp_set['keyword_data']:
                                        target_domain_keywords.append(
                                            resp_set['keyword_data']["keyword"]
                                        )
                except Exception as e:
                    # Log the exception but don't raise it
                    print(f"Exception Error in keyword scraping: {str(e)}")
                    pass
        else:
            # Log the error
            print(f"DataForSEO API Error. Code: {response.get('status_code', 'Unknown')} "
                  f"Message: {response.get('status_message', 'Unknown error')}")
        
        return target_domain_keywords
