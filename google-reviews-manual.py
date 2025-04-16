import requests
from bs4 import BeautifulSoup
import time
import random
import json
import re
from urllib.parse import urljoin

# Step 1: Define the search query
query = "Dr. Azadeh Beheshtian Interventional Cardiologist New York"

# Step 2: Construct the Google search URL
url = f"https://www.google.com/search?q={query}"

# Step 3: Set headers to mimic a real browser request
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
]
headers = {
    "User-Agent": random.choice(user_agents),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
}

# Step 4: Use ScrapeOps Proxy to avoid IP blocking
scrapeops_api_key = "37e23611-991c-480b-b769-3a8281be9e26"  # Replace with your actual API key
proxy_url = "https://proxy.scrapeops.io/v1/"

# Function to extract the title
def extract_title(panel):
    title_tag = panel.find('div', {'data-attrid': 'title'})
    return title_tag.get_text(strip=True) if title_tag else "Not Found"
# Function to extract the phone number
def extract_bio(panel):
    bio_tag = panel.find('span', {'E5BaQ'})
    return bio_tag.get_text(strip=True) if bio_tag  else "Not Found"
# Function to extract the rating and number of reviews
def extract_rating_and_reviews(panel):
    subtitle_tag = panel.find('div', {'data-attrid': 'subtitle'})
    rating, number_of_reviews = "Not Found", "Not Found"
    if subtitle_tag:
        subtitle_text = subtitle_tag.get_text(strip=True)
        rating_match = re.search(r"(\d+\.\d+)", subtitle_text)
        reviews_match = re.search(r"(\d+)\s+Google\s+reviews", subtitle_text)
        if rating_match:
            rating = float(rating_match.group(1))
        if reviews_match:
            number_of_reviews = int(reviews_match.group(1))
    return rating, number_of_reviews
# Function to extract the address
def extract_address(panel):
    address_tag = panel.find('div', {'data-attrid': 'kc:/location/location:address'})
    return address_tag.get_text(strip=True).replace("Address:", "").strip() if address_tag else "Not Found"
# Function to extract the phone number
def extract_phone(panel):
    phone_tag = panel.find('a', {'data-phone-number': True})
    return phone_tag['data-phone-number'] if phone_tag and 'data-phone-number' in phone_tag.attrs else "Not Found"
# Function to extract the website link
def extract_website(panel):
    website_tag = panel.find('a', {'class': 'n1obkb mI8Pwc'})
    return website_tag['href'] if website_tag and 'href' in website_tag.attrs else "Not Found"
# Function to extract business status (e.g., "Permanently closed")
def extract_business_status(panel):
    business_status_tag = panel.find('div', {'data-attrid': 'kc:/local:permanently closed'})
    status_text_tag = business_status_tag.find('span', {'class': 'hBA2d Shyhc'}) if business_status_tag else None
    return status_text_tag.get_text(strip=True) if status_text_tag else "Not Found"
# Function to extract the provider description
def extract_provider_description(panel):
    provider_description_tag = panel.find('div', {'data-attrid': 'kc:/local:merchant_description'})
    if provider_description_tag:
        pqboe_div = provider_description_tag.find('div', {'class': 'PQbOE'})
        description_div = pqboe_div.find_next_sibling('div') if pqboe_div else None
        description = description_div.get_text(strip=True) if description_div else "No description available"
        return description
    return "provider_description: No description available"
def extract_google_reviews(soup):
    """
    Extracts Google reviews data from the provided HTML structure.
    Returns a dictionary containing the section title and related terms (rating and total reviews).
    """
    google_reviews_data = {"section_title": "Google reviews", "related_terms": []}
    
    # Locate the Google reviews section
    google_reviews_section = soup.find('div', {'data-attrid': 'kc:/collection/knowledge_panels/local_reviewable:review_summary'})
    if google_reviews_section:
        print("Found 'Google reviews' section.")
        
        # Extract overall rating
        rating_tag = google_reviews_section.find('span', {'class': 'Aq14fc'})
        rating = rating_tag.get_text(strip=True) + "/5" if rating_tag else "No rating available"
        
        # Extract total number of reviews
        total_reviews_tag = google_reviews_section.find('a', {'jsaction': 'FNFY6c'})
        total_reviews = total_reviews_tag.get_text(strip=True) if total_reviews_tag else "No reviews available"
        
        # Append the extracted data to the related_terms list
        google_reviews_data['related_terms'].append({
            "rating": rating,
            "total_reviews": total_reviews
        })
    else:
        print("'Google reviews' section not found.")
    
    return google_reviews_data
# Function to extract "Reviews from the web"
def extract_web_reviews(panel):
    """
    Extracts "Reviews from the web" data from the provided HTML structure.
    Returns a dictionary containing the extracted reviews.
    """
    web_reviews_entities = {"web_reviews": []}
    
    # Locate the "Reviews from the web" section
    reviews_from_web_section = panel.find('div', {'data-attrid': 'kc:/location/location:third_party_aggregator_ratings'})
    if reviews_from_web_section:
        print("Found 'Reviews from the web' section.")
        
        # Extract individual review sources
        review_sources = reviews_from_web_section.find_all('a', {'class': 'DMxz8'})  # Updated class name
        for source in review_sources:
            # Extract rating
            rating_tag = source.find('span', {'class': 'inaKse G5rmf'})
            rating = rating_tag.get_text(strip=True) if rating_tag else "No rating available"
            
            # Extract title (e.g., "Healthgrades")
            title_tag = source.find('span', {'class': 'inaKse zLJMec'})
            title = title_tag.get_text(strip=True) if title_tag else "No title available"
            
            # Extract total reviews
            total_reviews_tag = source.find('span', {'class': 'inaKse KM6XSd'})
            total_reviews = total_reviews_tag.get_text(strip=True).replace("·", "").strip() if total_reviews_tag else "No reviews available"
            
            # Append the extracted data to the web_reviews_entities dictionary
            web_reviews_entities['web_reviews'].append({
                "rating": rating,
                "title": title,
                "total_reviews": total_reviews
            })
        
        print(f"Extracted {len(web_reviews_entities['web_reviews'])} review sources.")
    else:
        print("'Reviews from the web' section not found.")
    
    return web_reviews_entities
# def extract_images(media_section):
#     """Extracts image data from the media section."""
#     images = []
#     image_containers = media_section.find_all('a', href=True)
#     for container in image_containers:
#         img_tag = container.find('img')
#         if img_tag:
#             try:
#                 image_data = {
#                     "description": img_tag.get('alt', "No description"),
#                     "url": "https://www.google.com"+container['href']
#                 }
#                 images.append(image_data)
#             except KeyError as e:
#                 print(f"Missing attribute in image container: {e}")
#     return images
# def extract_map(media_section):
#     """Extracts map data from the media section."""
#     map_data = []
#     map_container = media_section.find('g-img', id='lu_map')
#     if map_container:
#         map_img_tag = map_container.find('img')
#         if map_img_tag:
#             try:
#                 map_data.append({
#                     "type": "map",
#                     "url": "https://www.google.com"+map_img_tag['src']
#                 })
#             except KeyError as e:
#                 print(f"Missing attribute in map container: {e}")
#     return map_data

def construct_full_url(base_url, relative_url):
    """
    Constructs a full URL by joining a base URL with a relative URL.
    Skips invalid or malformed URLs.
    """
    # Skip URLs that are malformed (e.g., missing slashes between base and relative URL)
    if not relative_url or re.match(r'^/+$', relative_url) or relative_url.startswith("data:image"):
        return None
    
    # Construct the full URL
    return urljoin(base_url, relative_url)

def extract_images(media_section):
    """Extracts image data from the media section."""
    images = []
    image_containers = media_section.find_all('a', href=True)
    for container in image_containers:
        img_tag = container.find('img')
        if img_tag:
            try:
                # Construct the full URL
                base_url = "https://www.google.com"
                full_url = construct_full_url(base_url, container.get('href'))
                
                # Only append if the URL is valid
                if full_url:
                    image_data = {
                        "description": img_tag.get('alt', "No description"),
                        "url": full_url
                    }
                    images.append(image_data)
            except Exception as e:
                print(f"Error processing image container: {e}")
    return images

def extract_map(media_section):
    """Extracts map data from the media section."""
    map_data = []
    map_container = media_section.find('g-img', id='lu_map')
    if map_container:
        map_img_tag = map_container.find('img')
        if map_img_tag:
            try:
                # Construct the full URL
                base_url = "https://www.google.com"
                full_url = construct_full_url(base_url, map_img_tag.get('src'))
                
                # Only append if the URL is valid
                if full_url:
                    map_data.append({
                        "type": "map",
                        "url": full_url
                    })
            except Exception as e:
                print(f"Error processing map container: {e}")
    return map_data

def extract_media_type(soup):
    # Extract media data
    media_section = soup.find('div', {'data-hveid': 'CBkQAA'})
    if media_section:
        print("Found 'Media' section.")
        images = extract_images(media_section)
        maps = extract_map(media_section)
        return images + maps
    else:
        print("'Media' section not found.")
        return None
def extract_people_also_search_for(soup):
    """Extracts data from the 'People also search for' section."""
    # Locate the section
    people_search_section = soup.find('div', {'data-attrid': 'kc:/local:sideways refinements'})
    related_entities = []

    if people_search_section:
        print("Found 'People also search for' section.")
        
        # Extract individual entities
        entities = people_search_section.find_all('div', class_='H93uF PZPZlf MRfBrb kno-vrt-t')
        for entity in entities:
            # Extract Name
            name_div = entity.find('div', class_='fl ellip oBrLN CYJS5e ZwRhJd')
            name = name_div.get_text(strip=True) if name_div else None
            
            # Extract Title/Profession
            title_div = entity.find('div', class_='xlBGCb ellip wYIIv')
            title = title_div.get_text(strip=True) if title_div else None
            
            # # Extract Image URL
            # img_tag = entity.find('img')
            # img_url = img_tag['src'] if img_tag and 'src' in img_tag.attrs else None
            
            # Append extracted details to the list
            related_entities.append({
                'name': name,
                'title': title
                # 'image_url': img_url
            })
    
    return {
        "section_title": "People also search for",
        "related_terms": related_entities
    }
def extract_knowledge_panel_data(panel, soup):
    data = {}

    # Extract first few items without delays
    data["title"] = extract_title(panel)
    data["rating"], data["number_of_google_reviews"] = extract_rating_and_reviews(panel)
    data["bio"] = extract_bio(panel)
    data["address"] = extract_address(panel)
    data["phone"] = extract_phone(panel)

    # Introduce a delay before extracting the last five items
    print("Sleeping before extracting the last five items...")
    time.sleep(3)  # Sleep for 5 seconds (adjust as needed)

    # Extract website
    data["website"] = extract_website(panel)

    # Sleep again before the next item
    print("Sleeping before extracting business status...")
    time.sleep(3)  # Sleep for 3 seconds (adjust as needed)

    # Extract business status
    data["business_status"] = extract_business_status(panel)

    # Sleep again before the next item
    print("Sleeping before extracting provider description...")
    time.sleep(3)  # Sleep for 3 seconds (adjust as needed)

    # Extract provider description
    data["provider_description"] = extract_provider_description(panel)

    # Sleep again before the next item
    print("Sleeping before extracting Google reviews...")
    time.sleep(3)  # Sleep for 5 seconds (adjust as needed)

    # Extract Google reviews
    data["google_reviews"] = extract_google_reviews(soup)

    # Sleep again before the next item
    print("Sleeping before extracting media type...")
    time.sleep(random.randint(5, 15))

    # Extract media type
    data["media_type"] = extract_media_type(soup)

    # Sleep again before the next item
    print("Sleeping before extracting 'People also search for'...")
    time.sleep(random.randint(5, 9))

    # Extract "People also search for"
    data["people_also_search_for"] = extract_people_also_search_for(soup)

    # Sleep again before the final item
    print("Sleeping before extracting 'Web reviews'...")
    time.sleep(random.randint(5, 9))

    # Extract "Web reviews"
    data["web_reviews"] = extract_web_reviews(panel)

    # Add query to the data dictionary
    data["query"] = query

    return data
# Save the extracted data to a JSON file
def save_to_json(data, query):
    """Saves the extracted data to a JSON file named after the query."""
    filename = re.sub(r'[^\w\-_\. ]', '_', query) + '.json'
    print(f"Saving data to file: {filename}")
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"Data successfully saved to {filename}")
    except Exception as e:
        print(f"Failed to save JSON file: {e}")

# Retry mechanism
max_retries = 7  # Maximum number of retries
retry_delay = 15  # Delay between retries in seconds

for attempt in range(max_retries):
    print(f"Attempt {attempt + 1} of {max_retries}")
    # Add a random delay before each request
    time.sleep(random.uniform(7, 15))

    try:
        # Send the GET request through ScrapeOps Proxy
        response = requests.get(
            url=proxy_url,
            params={"api_key": scrapeops_api_key, "url": url},  # The target URL to scrape
            headers=headers,
        )
        response.raise_for_status()  # Raise an exception for HTTP errors

        # Parse the HTML content with BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')

        # Save the raw HTML for debugging
        with open("google_search.html", "w", encoding="utf-8") as file:
            file.write(soup.prettify())
        print("Raw HTML saved to 'google_search.html' for debugging.")

        # Attempt to locate the Knowledge Panel
        knowledge_panel = soup.find('div', {'id': 'rhs'})
        if not knowledge_panel:
            print("Knowledge Panel not found. Retrying...")
            continue  # Retry the request
        print("Knowledge Panel found!")
        break  # Exit the retry loop if the Knowledge Panel is found

    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching the data: {e}")
        if attempt < max_retries - 1:
            print(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
        else:
            print("Max retries reached. Exiting.")
            exit()
else:
    # If the loop completes without finding the Knowledge Panel
    print("Failed to find the Knowledge Panel after multiple attempts.")
    exit()

# Extract data from the Knowledge Panel
panel_data = extract_knowledge_panel_data(knowledge_panel, soup)

# Save the extracted data
save_to_json(panel_data, query)