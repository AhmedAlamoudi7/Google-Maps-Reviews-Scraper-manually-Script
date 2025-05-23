import requests
from bs4 import BeautifulSoup
import time
import random
import json
import re
from urllib.parse import urljoin
import csv
import os
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
import argparse
import logging
import html

# Configure logging
logging.basicConfig(
    filename="scraping.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Set headers to mimic a real browser request
headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
}

# ScrapeOps Proxy
scrapeops_api_key = "daeff0a6-4bba-4f67-8e03-1a46f9913ac2"
proxy_url = "https://proxy.scrapeops.io/v1/"


# Function to extract the title
def extract_title(panel):
    title_tag = panel.find("div", {"data-attrid": "title"})
    if not title_tag:
        title_tag = panel.find("h2", {"data-attrid": "title"})

    return title_tag.get_text(strip=True) if title_tag else ""


# Function to extract the phone number
def extract_bio(panel):
    bio_tag = panel.find("span", {"E5BaQ"})
    if not bio_tag:
        bio_tag = panel.find("div", {"data-attrid": "kc:/local:one line summary"})
    return bio_tag.get_text(strip=True) if bio_tag else ""


# Function to extract the rating and number of reviews
def extract_rating_and_reviews(panel):
    # Initialize default values
    rating, number_of_reviews = "", ""

    # Extract rating from subtitle (if available)
    subtitle_tag = panel.find("div", {"data-attrid": "subtitle"})
    if subtitle_tag:
        subtitle_text = subtitle_tag.get_text(strip=True)
        rating_match = re.search(r"(\d+\.\d+)", subtitle_text)
        if rating_match:
            rating = float(rating_match.group(1))
    if not rating:
        # Extract rating and number of reviews from the div containing the rating information
        rating_div = panel.find("div", class_="ChPIuf YrbPuc")
        if rating_div:
            # Extract rating (e.g., 4.8)
            rating_span = rating_div.find("span", class_="yi40Hd YrbPuc")
            if rating_span:
                rating_text = rating_span.get_text(strip=True)
                try:
                    rating = float(rating_text)
                except ValueError:
                    rating = ""  # In case the text is not a valid float
    if not rating:
        # Extract rating and number of reviews from the div containing the rating information
        rating_div = panel.find(
            "div",
            {
                "data-attrid": "kc:/collection/knowledge_panels/local_reviewable:star_score"
            },
        )
        if rating_div:
            # Extract rating (e.g., 4.8)
            rating_span = rating_div.find("span", class_="Aq14fc")
            if rating_span:
                rating_text = rating_span.get_text(strip=True)
                try:
                    rating = float(rating_text)
                except ValueError:
                    rating = ""  # In case the text is not a valid float

    # Extract number of reviews from the <a> tag
    review_tag = panel.find("a", {"data-async-trigger": "reviewDialog"})
    if review_tag:
        review_text = review_tag.get_text(strip=True)
        reviews_match = re.search(r"(\d+)\s+Google\s+reviews", review_text)
        if not reviews_match:
            reviews_match = re.search(r"(\d+)\s+Google\s+review", review_text)
        if reviews_match:
            number_of_reviews = int(reviews_match.group(1))

    return rating, number_of_reviews


# Function to extract the address
def extract_address(panel):
    address_tag = panel.find("div", {"data-attrid": "kc:/location/location:address"})
    return (
        address_tag.get_text(strip=True).replace("Address:", "").strip()
        if address_tag
        else ""
    )


# Function to extract the phone number
def extract_phone(panel):
    phone_tag = panel.find("a", {"data-phone-number": True})
    return (
        phone_tag["data-phone-number"]
        if phone_tag and "data-phone-number" in phone_tag.attrs
        else ""
    )


# Function to extract the website link
def extract_website(panel):
    website_tag = panel.find("a", {"class": "n1obkb mI8Pwc"})
    return website_tag["href"] if website_tag and "href" in website_tag.attrs else ""


# Function to extract business status (e.g., "Permanently closed")
def extract_business_status(panel):
    business_status_tag = panel.find(
        "div", {"data-attrid": "kc:/local:permanently closed"}
    )
    status_text_tag = (
        business_status_tag.find("span", {"class": "hBA2d Shyhc"})
        if business_status_tag
        else None
    )
    return status_text_tag.get_text(strip=True) if status_text_tag else "Active"


# Function to extract the provider description
def extract_provider_description(panel):
    provider_description_tag = panel.find(
        "div", {"data-attrid": "kc:/local:merchant_description"}
    )
    if provider_description_tag:
        pqboe_div = provider_description_tag.find("div", {"class": "PQbOE"})
        description_div = pqboe_div.find_next_sibling("div") if pqboe_div else None
        description = description_div.get_text(strip=True) if description_div else ""
        return description
    return ""


def extract_google_reviews(soup):
    """
    Extracts Google reviews data from the provided HTML structure.
    Returns a dictionary containing the section title and related terms (rating and total reviews).
    """
    google_reviews_data = {"section_title": "Google reviews", "related_terms": []}

    # Locate the Google reviews section
    google_reviews_section = soup.find(
        "div",
        {
            "data-attrid": "kc:/collection/knowledge_panels/local_reviewable:review_summary"
        },
    )
    if google_reviews_section:
        print("Found 'Google reviews' section.")

        # Extract overall rating
        rating_tag = google_reviews_section.find("span", {"class": "Aq14fc"})
        rating = rating_tag.get_text(strip=True) + "/5" if rating_tag else ""

        # Extract total number of reviews
        review_tag = soup.find("a", {"data-async-trigger": "reviewDialog"})
        if review_tag:
            review_text = review_tag.get_text(strip=True)
            reviews_match = re.search(r"(\d+)\s+Google\s+reviews", review_text)
            if not reviews_match:
                reviews_match = re.search(r"(\d+)\s+Google\s+review", review_text)
            if reviews_match:
                total_reviews = int(reviews_match.group(1))

        # Append the extracted data to the related_terms list
        google_reviews_data["related_terms"].append(
            {"rating": rating, "total_reviews": total_reviews}
        )
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
    reviews_from_web_section = panel.find(
        "div", {"data-attrid": "kc:/location/location:third_party_aggregator_ratings"}
    )
    if reviews_from_web_section:
        print("Found 'Reviews from the web' section.")

        # Extract individual review sources
        review_sources = reviews_from_web_section.find_all(
            "a", {"class": "DMxz8"}
        )  # Updated class name
        for source in review_sources:
            # Extract rating
            rating_tag = source.find("span", {"class": "inaKse G5rmf"})
            rating = rating_tag.get_text(strip=True) if rating_tag else ""

            # Extract title (e.g., "Healthgrades")
            title_tag = source.find("span", {"class": "inaKse zLJMec"})
            title = title_tag.get_text(strip=True) if title_tag else ""

            # Extract total reviews
            total_reviews_tag = source.find("span", {"class": "inaKse KM6XSd"})
            total_reviews = (
                total_reviews_tag.get_text(strip=True).replace("·", "").strip()
                if total_reviews_tag
                else ""
            )

            # Append the extracted data to the web_reviews_entities dictionary
            web_reviews_entities["web_reviews"].append(
                {"rating": rating, "title": title, "total_reviews": total_reviews}
            )

        print(f"Extracted {len(web_reviews_entities['web_reviews'])} review sources.")
    else:
        print("'Reviews from the web' section not found.")

    return web_reviews_entities


def construct_full_url(base_url, relative_url):
    """
    Constructs a full URL by joining a base URL with a relative URL.
    Skips invalid or malformed URLs.
    """
    # Skip URLs that are malformed (e.g., missing slashes between base and relative URL)
    if (
        not relative_url
        or re.match(r"^/+$", relative_url)
        or relative_url.startswith("data:image")
    ):
        return None

    # Construct the full URL
    return urljoin(base_url, relative_url)


def extract_images(media_section):
    """Extracts image data from the media section."""
    images = []
    image_containers = media_section.find_all("a", href=True)
    for container in image_containers:
        img_tag = container.find("img")
        if img_tag:
            try:
                # Construct the full URL
                base_url = "https://www.google.com"
                full_url = construct_full_url(base_url, container.get("href"))

                # Only append if the URL is valid
                if full_url:
                    image_data = {
                        "description": img_tag.get("alt", ""),
                        "url": full_url,
                    }
                    images.append(image_data)
            except Exception as e:
                print(f"Error processing image container: {e}")
    return images


def extract_map(media_section):
    """Extracts map data from the media section."""
    map_data = []
    map_container = media_section.find("g-img", id="lu_map")
    if map_container:
        map_img_tag = map_container.find("img")
        if map_img_tag:
            try:
                # Construct the full URL
                base_url = "https://www.google.com"
                full_url = construct_full_url(base_url, map_img_tag.get("src"))

                # Only append if the URL is valid
                if full_url:
                    map_data.append({"type": "map", "url": full_url})
            except Exception as e:
                print(f"Error processing map container: {e}")
    return map_data


def extract_media_type(soup):
    # Extract media data
    media_section = soup.find("div", {"data-hveid": "CBkQAA"})
    if media_section:
        print("Found 'Media' section.")
        images = extract_images(media_section)
        maps = extract_map(media_section)
        return images + maps
    else:
        print("'Media' section not found.")
        return None
    
#     return result
def extract_people_also_search_for(soup):
    """
    Extracts 'People also search for' section from Google search result page.
    """
    result = {"section_title": "People also search for", "related_terms": []}

    # Locate the 'People also search for' container
    container = soup.find(
        "div", attrs={"data-attrid": "kc:/local:sideways refinements"}
    )
    if not container:
        print("No 'People also search for' section found.")
        return result

    # Find all related person tiles
    person_tiles = container.find_all("div", class_="H93uF PZPZlf MRfBrb kno-vrt-t")
    print(f"Found {len(person_tiles)} related entities.")

    for tile in person_tiles:
        name_tag = tile.find("div", class_="fl ellip oBrLN CYJS5e ZwRhJd")
        title_tag = tile.find("div", class_="xlBGCb ellip wYIIv")

        name = name_tag.get_text(strip=True) if name_tag else None
        title = title_tag.get_text(strip=True) if title_tag else None

        if name:
            result["related_terms"].append({"name": name, "title": title})

    return result


def extract_opening_hours_from_html(html_text):
    pattern = re.compile(
        r"window\.jsl\.dh\('([^']*)','(.+?)'\);",  # capture the second argument
        re.DOTALL,
    )

    matches = pattern.findall(html_text)

    for match_id, encoded_html in matches:
        if "WgFkxc" in encoded_html:  # heuristic: match the table with hours
            decoded_html = (
                encoded_html.encode("utf-8")
                .decode("unicode_escape")  # decode \u202f and \x3c etc.
                .replace(r"\'", "'")  # unescape any JS-escaped single quotes
            )
            print(decoded_html)
            return extract_opening_hours(decoded_html)

    return {}


def extract_opening_hours(html_text):
    html_text = html.unescape(html_text)

    # Match rows of the table: <td>Day</td><td>Time</td>
    pattern = re.compile(
        r"<tr[^>]*>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>", re.DOTALL
    )

    matches = pattern.findall(html_text)
    hours = {}
    for day, time in matches:
        # Clean up inner <div> for holidays like "(Easter)"
        day_clean = re.sub(r"<div.*?</div>", "", day, flags=re.DOTALL)
        hours[day_clean.strip()] = time.strip()

    return hours


def extract_hours(panel):
    """
    Extracts the "Hours" data from the provided HTML structure.
    Returns a dictionary containing the extracted hours information.
    """
    hours_data = {
        "section_title": "",
        "current_status": "",
    }

    # Locate the "Hours" section
    hours_section = panel.find("div", {"data-attrid": "kc:/location/location:hours"})
    if not hours_section:
        print("'Hours' section not found.")
        return hours_data

    print("Found 'Hours' section.")

    try:
        # Extract current status (e.g., "Closed ⋅ Opens 9 AM")
        current_status_tag = hours_section.find("span", {"class": "TLou0b"})
        if current_status_tag:
            current_status = current_status_tag.get_text(strip=True)
            hours_data["current_status"] = current_status
            print(f"Current status: {current_status}")

    except Exception as e:
        print(f"An error occurred while extracting hours data: {e}")

    return hours_data


def extract_social_media_profiles(panel):
    """
    Extracts social media profiles data from the provided HTML structure.
    Returns a dictionary containing the extracted profiles.
    """
    social_media_profiles = {"social_media": []}

    # Locate the "Social Media Presence" section
    social_media_section = panel.find(
        "div", {"data-attrid": "kc:/common/topic:social media presence"}
    )
    if social_media_section:
        print("Found 'Social Media Presence' section.")

        # Extract individual social media profiles
        profile_containers = social_media_section.find_all(
            "div", {"class": "PZPZlf dRrfkf kno-vrt-t"}
        )
        for container in profile_containers:
            # Extract the link
            link_tag = container.find("a")
            if link_tag:
                url = link_tag["href"]
                platform_name = (
                    link_tag.find("div", {"class": "CtCigf"}).get_text(strip=True)
                    if link_tag.find("div", {"class": "CtCigf"})
                    else ""
                )

                # Append the extracted data to the social_media_profiles dictionary
                social_media_profiles["social_media"].append(
                    {"platform": platform_name, "url": url}
                )

        print(
            f"Extracted {len(social_media_profiles['social_media'])} social media profiles."
        )
    else:
        print("'Social Media Presence' section not found.")

    return social_media_profiles


def extract_contact_info(panel):
    """
    Extracts contact information (e.g., appointment links) from the provided HTML structure.
    Returns a dictionary containing the extracted contact details.
    """
    contact_data = {"contact": []}

    # Locate the "Contact" section
    contact_section = panel.find(
        "div", {"class": "wDYxhc NFQFxe", "data-attrid": "kc:/local:appointment"}
    )
    if contact_section:
        print("Found 'Contact' section.")

        # Extract the appointment link
        appointment_link_tag = contact_section.find("a")
        if appointment_link_tag:
            appointment_url = appointment_link_tag["href"]
            appointment_text = appointment_link_tag.get_text(strip=True)

            # Append the extracted data to the contact_data dictionary
            contact_data["contact"].append(
                {
                    "type": "Appointment",
                    "url": appointment_url,
                    "text": appointment_text,
                }
            )

        print(f"Extracted {len(contact_data['contact'])} contact details.")
    else:
        print("'Contact' section not found.")

    return contact_data


def extract_google_reviews_list(panel):
    """
    Extracts Google reviews data from the provided HTML structure.
    Returns a dictionary containing the extracted reviews.
    """
    google_reviews_data = {"section_title": "Google reviews", "reviews": []}

    # Locate the Google reviews section
    google_reviews_section = panel.find(
        "div",
        {
            "data-attrid": "kc:/collection/knowledge_panels/local_reviewable:review_summary"
        },
    )
    if google_reviews_section:
        print("Found 'Google reviews' section.")

        # Extract individual reviews
        review_containers = google_reviews_section.find_all("div", {"class": "RfWLue"})
        for container in review_containers:

            # Extract user name
            user_name_tag = container.find("a", {"class": "a-no-hover-decoration"})
            user_name = user_name_tag.get_text(strip=True) if user_name_tag else ""

            # Extract review text
            review_text_tag = user_name_tag
            review_text = (
                review_text_tag.get_text(strip=True) if review_text_tag else ""
            )

            # Extract rating
            rating_tag = container.find("span", {"class": "z3HNkc"})
            rating = (
                rating_tag["aria-label"]
                if rating_tag and "aria-label" in rating_tag.attrs
                else ""
            )

            # Append the extracted data to the google_reviews_data dictionary
            google_reviews_data["reviews"].append(
                {"user_name": user_name, "review_text": review_text, "rating": rating}
            )

        print(f"Extracted {len(google_reviews_data['reviews'])} reviews.")
    else:
        print("'Google reviews' section not found.")

    return google_reviews_data


def extract_knowledge_panel_data(panel, soup, query, html_text):
    data = {}
    # Extract first few items without delays
    data["title"] = extract_title(panel)
    data["rating"], data["number_of_google_reviews"] = extract_rating_and_reviews(panel)
    data["bio"] = extract_bio(panel)
    data["address"] = extract_address(panel)
    data["phone"] = extract_phone(panel)
    # Extract website
    data["website"] = extract_website(panel)
    # Extract business status
    data["business_status"] = extract_business_status(panel)
    # Extract provider description
    data["provider_description"] = extract_provider_description(panel)
    # Extract hours
    data["hours"] = extract_opening_hours_from_html(html_text)
    # Extract contact
    data["contact"] = extract_contact_info(panel)
    # Extract profiles
    data["profiles"] = extract_social_media_profiles(panel)
    # Extract Google reviews
    data["google_reviews"] = extract_google_reviews(soup)
    # Extract Google reviews list
    data["google_reviews_list"] = extract_google_reviews_list(soup)
    # Extract media type
    data["media_type"] = extract_media_type(soup)
    # Extract "People also search for"
    data["people_also_search_for"] = extract_people_also_search_for(soup)
    # Extract "Web reviews"
    data["web_reviews"] = extract_web_reviews(panel)
    # Add query to the data dictionary
    data["query"] = query

    return data


def save_to_json(data, query, output_directory):
    """Saves the extracted data to a JSON file named after the query."""
    os.makedirs(output_directory, exist_ok=True)
    filename = re.sub(r"[^\w\-_\. ]", "_", query) + ".json"
    filepath = os.path.join(output_directory, filename)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"Data successfully saved to {filepath}")
    except Exception as e:
        logging.error(f"Failed to save JSON file for query '{query}': {e}")


def process_query(query_text, npi, output_directory):
    print(f"Processing query: {query_text}")
    max_retries = 5
    retry_delay = 15

    # Ensure the output directory exists
    os.makedirs(output_directory, exist_ok=True)

    for attempt in range(max_retries):
        print(f"Attempt {attempt + 1} of {max_retries}")
        time.sleep(random.uniform(7, 15))
        try:
            response = requests.get(
                url=proxy_url,
                params={
                    "api_key": scrapeops_api_key,
                    "url": f"https://www.google.com/search?q={query_text}",
                },
                headers=headers,
                verify=False,  # Disable SSL verification
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            # Save the raw HTML to a file in the output directory
            html_filename = os.path.join(
                output_directory, f"{query_text.replace(' ', '_')}_raw.html"
            )
            with open(html_filename, "w", encoding="utf-8") as html_file:
                html_file.write(soup.prettify())
            print(f"Raw HTML saved to '{html_filename}'")

            # Locate the Knowledge Panel
            knowledge_panel = soup.find("div", {"id": "rhs"})
            if not knowledge_panel:
                print("Knowledge Panel not found. Retrying...")
                continue
            print("Knowledge Panel found!")
            break
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching data for query '{query_text}': {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("Max retries reached. Skipping this query.")
                return None
    else:
        logging.error(
            f"Failed to find Knowledge Panel for query '{query_text}' after multiple attempts."
        )
        return None

    # Extract data from the Knowledge Panel
    panel_data = extract_knowledge_panel_data(
        knowledge_panel, soup, query_text, response.text
    )
    if npi:
        panel_data["npi"] = npi

    # Save the extracted data to JSON
    save_to_json(panel_data, query_text, output_directory)

    return True


def fetch_all_data(csv_file, output_directory, max_threads=10):
    completed_queries = set()
    progress_file = os.path.join(output_directory, "progress.txt")

    if os.path.exists(progress_file):
        with open(progress_file, "r") as f:
            completed_queries = {line.strip() for line in f}
        print(
            f"Loaded {len(completed_queries)} completed queries from {progress_file}."
        )
    else:
        print("No progress file found. Starting fresh.")

    with open(csv_file, mode="r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    remaining_rows = [row for row in rows if row["query_id"] not in completed_queries]
    print(f"Found {len(remaining_rows)} unprocessed queries.")

    with tqdm(total=len(remaining_rows), desc="Processing Queries") as progress_bar:
        with ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures = []
            for row in remaining_rows:
                query_id = row["query_id"]
                query_text = row["query_text"]
                npi = row.get("npi", None)
                future = executor.submit(
                    process_query, query_text, npi, output_directory
                )
                futures.append((future, query_id))

            for future, query_id in futures:
                try:
                    success = future.result()
                    if success:
                        with open(progress_file, "a") as f:
                            f.write(f"{query_id}\n")
                        print(f"Query ID {query_id} successfully processed.")
                    else:
                        print(f"Query ID {query_id} failed. Skipping...")
                except Exception as e:
                    logging.error(f"Error processing query ID {query_id}: {e}")
                finally:
                    progress_bar.update(1)

    print("Processing complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Process queries from a CSV file and extract data from Google Knowledge Panels."
    )
    parser.add_argument(
        "--csv", required=True, help="Path to the CSV file containing queries."
    )
    parser.add_argument(
        "--output", default="output", help="Directory to save JSON output files."
    )
    parser.add_argument(
        "--threads",
        type=int,
        default=10,
        help="Number of threads to use for processing queries.",
    )
    args = parser.parse_args()

    if not scrapeops_api_key:
        raise ValueError("SCRAPEOPS_API_KEY environment variable is not set.")

    fetch_all_data(args.csv, args.output, args.threads)
