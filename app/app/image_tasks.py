import urllib.request
import json

def fetch_images(query: str):
    # Define the API endpoint
    base_url = 'http://search.tosiehgar.ir/search'
    params = f"?q={query}&format=json&categories=images"
    url = base_url + params

    try:
        # Make a request to the API using urllib
        with urllib.request.urlopen(url) as response:
            if response.status != 200:
                return {"error": f"Failed to fetch data: {response.status}"}
            
            # Read the response
            json_data = response.read().decode('utf-8')

        # Since the response is in JSON format, there's no need to use BeautifulSoup.
        # Parse the JSON response
        data = json.loads(json_data)

        if 'results' not in data:
            return {"error": f"Unexpected JSON structure: {data}"}

        return data

    except urllib.error.URLError as e:
        return {"error": f"An error occurred: {e}"}

# Example usage
# images_data = fetch_images('hello')
# print(images_data)