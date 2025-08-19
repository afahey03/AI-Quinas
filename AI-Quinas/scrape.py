import requests
from bs4 import BeautifulSoup
import time
import os
import re
import random

def get_default_end_question(part):
    """Returns the default end question number based on the part of the Summa"""
    part_question_counts = {
        "I": 119,      # Prima Pars has 119 questions
        "II-I": 114,   # Prima Secundae has 114 questions
        "II-II": 189,  # Secunda Secundae has 189 questions
        "III": 90      # Tertia Pars has 90 questions
    }
    return part_question_counts.get(part, 119)  # Default to 119 if part not found

def get_article_count(part, question):
    """Returns known article counts for specific questions"""
    special_cases = {
        "I": {
            119: 2,    # Question 119 in Prima Pars has 2 articles
        },
        "II-I": {
            114: 10,   # Question 114 in Prima Secundae has 10 articles
        },
        "II-II": {
            189: 10,   # Question 189 in Secunda Secundae has 10 articles
        },
        "III": {
            90: 4,     # Question 90 in Tertia Pars has 4 articles
        }
    }
    
    if part in special_cases and question in special_cases[part]:
        return special_cases[part][question]
    return None  # No special case

def get_part_url_format(part):
    """Returns the correct URL format for the given part"""
    # The website uses different formats for different parts
    part_formats = {
        "I": "I",           # Prima Pars: ST.I.Q1
        "II-I": "I-II",     # Prima Secundae: ST.I-II.Q1 (not ST.II-I.Q1)
        "II-II": "II-II",   # Secunda Secundae: ST.II-II.Q1
        "III": "III"        # Tertia Pars: ST.III.Q1
    }
    return part_formats.get(part, part)

def get_part_title(part):
    """Returns the title for the given part"""
    part_titles = {
        "I": "FIRST PART",
        "II-I": "FIRST PART OF THE SECOND PART",
        "II-II": "SECOND PART OF THE SECOND PART",
        "III": "THIRD PART"
    }
    return part_titles.get(part, f"PART {part}")

def get_part_subtitle(part):
    """Returns the subtitle for the given part"""
    part_subtitles = {
        "I": "SACRED DOCTRINE",
        "II-I": "MAN'S LAST END",
        "II-II": "FAITH, HOPE, AND CHARITY",
        "III": "THE INCARNATION"
    }
    return part_subtitles.get(part, "")

def scrape_summa(output_file, part="I", start_q=1, end_q=None, delay=0, verbose=False):
    """
    Scrape the Summa Theologica from Aquinas.cc preserving the exact format
    
    Parameters:
    - output_file: Path to the output text file
    - part: Part of the Summa ("I" for Prima Pars, "II-I" for Prima Secundae, etc.)
    - start_q: First question to scrape
    - end_q: Last question to scrape (defaults to max questions for the selected part)
    - delay: Seconds to wait between requests (default: 0)
    - verbose: Whether to print detailed progress messages (default: False)
    """
    # Set default end question based on the part if not specified
    if end_q is None:
        end_q = get_default_end_question(part)
    
    # Get the correct URL format for the part
    url_part = get_part_url_format(part)
    
    # Create directory for output file if it doesn't exist
    os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else '.', exist_ok=True)

    # Get the title and subtitle for this part
    part_title = get_part_title(part)
    part_subtitle = get_part_subtitle(part)
    
    if verbose:
        print(f"Starting scrape for part: {part} ({part_title})")
        print(f"Using URL part format: {url_part}")
        print(f"Questions range: {start_q} to {end_q}")

    # Open the output file
    with open(output_file, "w", encoding="utf-8") as f:
        # Write title
        f.write(f"SUMMA THEOLOGIAE {part_title}\n\n")
        
        # Write subtitle
        f.write(f"{part_subtitle}\n\n")
        
        # If this is the first question of the part, try to get the prologue
        if start_q == 1:
            try:
                # Try to get the part prologue
                part_url = f"https://aquinas.cc/la/en/~ST.{url_part}"
                resp = requests.get(part_url, timeout=60)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    
                    # Look for prologue content
                    prologue_content = []
                    
                    # Find all content paragraphs before the first question
                    for element in soup.find_all("vl-c", class_=lambda c: c and c.startswith("c2-2")):
                        text = element.text.strip()
                        if "question 1" in text.lower() or "q1" in text.lower():
                            break
                        if text and len(text) > 20 and "PART" not in text.upper() and not text.startswith("ST."):
                            prologue_content.append(text)
                    
                    # If we found prologue content, write it
                    if prologue_content:
                        f.write("PROLOGUE\n\n")
                        for text in prologue_content:
                            f.write(f"{text}\n\n")
            except Exception as e:
                if verbose:
                    print(f"Error getting prologue: {str(e)}")

        print(f"Scraping Summa Theologica Part {part}, Questions {start_q}-{end_q}...")

        for q_num in range(start_q, end_q + 1):
            if verbose:
                print(f"Scraping Question {q_num} from Part {part}...")
            
            # Get the question page
            question_url = f"https://aquinas.cc/la/en/~ST.{url_part}.Q{q_num}"
            if verbose:
                print(f"  Accessing URL: {question_url}")
                
            try:
                # Add user agent and vary request patterns to avoid blocking
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
                }
                response = requests.get(question_url, headers=headers, timeout=90)
                
                if response.status_code == 200:
                    # Parse the main question page
                    soup = BeautifulSoup(response.text, "html.parser")
                    
                    # Write question header
                    f.write(f"Question {q_num}\n")
                    
                    # Extract the question title
                    question_title = None
                    title_elem = soup.find("vl-c", class_=lambda c: c and "t-r" in c and c.startswith("c2-2"))
                    if title_elem:
                        question_title = title_elem.text.strip()
                        f.write(f"{question_title}\n\n")
                    
                    # Get the question description and points of inquiry
                    description_paras = []
                    inquiry_header = None
                    inquiry_items = []
                    
                    # Examine each content element
                    for element in soup.find_all("vl-c", class_=lambda c: c and c.startswith("c2-2")):
                        text = element.text.strip()
                        if not text:
                            continue
                        
                        # Skip elements that are likely not part of the description
                        if "article" in text.lower() and len(text) < 30:
                            continue
                            
                        # Check if this is an inquiry list header
                        if ("points of inquiry" in text.lower() or "inquir" in text.lower()) and not inquiry_header:
                            inquiry_header = text
                            continue
                            
                        # Check if this is an inquiry list item
                        if inquiry_header and (re.match(r'^\(\d+\)', text) or re.match(r'^\d+\.', text)):
                            inquiry_items.append(text)
                            continue
                            
                        # If we haven't found the inquiry header yet, this might be description text
                        if not inquiry_header and len(text) > 30 and not text.startswith("Article"):
                            description_paras.append(text)
                    
                    # Write the description paragraphs
                    for para in description_paras:
                        f.write(f"{para}\n\n")
                    
                    # Write the inquiry header and items
                    if inquiry_header:
                        f.write(f"{inquiry_header}\n\n")
                        for item in inquiry_items:
                            f.write(f"{item}\n")
                        f.write("\n")
                    
                    # Now determine how many articles are in this question
                    # First check if this is a special case with known article count
                    known_article_count = get_article_count(part, q_num)
                    
                    if known_article_count:
                        num_articles = known_article_count
                        if verbose:
                            print(f"  Using known article count for Q{q_num}: {num_articles} articles")
                    else:
                        # Try to detect the number of articles
                        article_nums = set()
                        
                        # Check for article links
                        article_pattern = re.compile(f"ST\\.{re.escape(url_part)}\\.Q{q_num}\\.A(\\d+)")
                        for link in soup.find_all("a", href=lambda href: href and article_pattern.search(href)):
                            match = article_pattern.search(link['href'])
                            if match:
                                article_nums.add(int(match.group(1)))
                        
                        # Check for article headers in the content
                        for header in soup.find_all("vl-c", class_=lambda c: c and "t-i" in c and c.startswith("c2-2")):
                            match = re.search(r'Article (\d+)', header.text)
                            if match:
                                article_nums.add(int(match.group(1)))
                        
                        # Additional check for links in the text
                        for element in soup.find_all(string=re.compile(r'Article \d+')):
                            matches = re.findall(r'Article (\d+)', element)
                            for match in matches:
                                article_nums.add(int(match))
                        
                        # Determine the number of articles
                        if article_nums:
                            num_articles = max(article_nums)
                            if verbose:
                                print(f"  Detected {num_articles} articles: {sorted(article_nums)}")
                        else:
                            # If we're at the last question, it might have more articles
                            if q_num == end_q:
                                num_articles = 10  # Assume 10 articles for the last question if we can't detect
                            else:
                                num_articles = 4  # Default for most questions
                            if verbose:
                                print(f"  Could not detect articles, using default: {num_articles}")
                    
                    # Special handling for the last questions of each part
                    if q_num == end_q:
                        # Last question of each part needs special attention
                        if verbose:
                            print(f"  Special handling for last question {q_num} of part {part}")
                        # For II-II Q189, ensure we get all 10 articles
                        if part == "II-II" and q_num == 189:
                            num_articles = 10
                        # For III Q90, ensure we get all 4 articles
                        elif part == "III" and q_num == 90:
                            num_articles = 4
                    
                    # Process each article with improved robustness
                    for article_num in range(1, num_articles + 1):
                        article_url = f"https://aquinas.cc/la/en/~ST.{url_part}.Q{q_num}.A{article_num}"
                        
                        if verbose:
                            print(f"    Processing Article {article_num} from {article_url}")
                        
                        retry_count = 0
                        max_retries = 7  # More retries for reliability
                        article_retrieved = False
                        
                        while not article_retrieved and retry_count < max_retries:
                            try:
                                # Add varied user agent and add randomization to avoid blocking
                                headers = {
                                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                                    "Accept-Language": "en-US,en;q=0.5"
                                }
                                
                                # Random delay between 1-3 seconds to avoid rate limiting
                                if retry_count > 0:
                                    time.sleep(1 + random.random() * 2)
                                
                                article_resp = requests.get(article_url, headers=headers, timeout=120)  # Longer timeout
                                
                                if article_resp.status_code == 200:
                                    article_retrieved = True
                                    article_soup = BeautifulSoup(article_resp.text, "html.parser")
                                    
                                    # Write article header
                                    f.write(f"Article {article_num}\n")
                                    
                                    # Extract article title
                                    article_title = None
                                    title_elem = article_soup.find("vl-c", class_=lambda c: c and "t-s" in c and c.startswith("c2-2"))
                                    if title_elem:
                                        article_title = title_elem.text.strip()
                                        f.write(f"{article_title}\n\n")
                                    else:
                                        # Try alternate ways to find the title
                                        for cls in ["t-h", "t-o"]:  # Try other class types
                                            title_elem = article_soup.find("vl-c", class_=lambda c: c and cls in c and c.startswith("c2-2"))
                                            if title_elem and title_elem.text.strip():
                                                article_title = title_elem.text.strip()
                                                f.write(f"{article_title}\n\n")
                                                break
                                    
                                    # Get all content elements for this article
                                    content_elements = article_soup.find_all("vl-c", class_=lambda c: c and c.startswith("c2-2"))
                                    
                                    # Track which texts we've already processed to avoid duplication
                                    processed_texts = set()
                                    
                                    # Process the article content in order, keeping original formatting
                                    for element in content_elements:
                                        text = element.text.strip()
                                        if not text or len(text) < 15 or text in processed_texts:
                                            continue
                                            
                                        # Skip article title or headers
                                        if (article_title and text == article_title) or text.startswith(f"Article {article_num}"):
                                            continue
                                        
                                        # Write the text as it appears
                                        f.write(f"{text}\n\n")
                                        processed_texts.add(text)
                                    
                                    # Fallback for rare cases: if we didn't get any content, try extracting direct from HTML
                                    if len(processed_texts) == 0:
                                        if verbose:
                                            print(f"    WARNING: No content found, trying direct HTML extraction")
                                        
                                        paragraphs = article_soup.select("div.body div.content p")
                                        for p in paragraphs:
                                            text = p.text.strip()
                                            if text and len(text) > 20 and text not in processed_texts:
                                                f.write(f"{text}\n\n")
                                                processed_texts.add(text)
                                        
                                        # If still no content, try extracting any text blocks
                                        if len(processed_texts) == 0:
                                            all_text = article_soup.get_text()
                                            lines = [line.strip() for line in all_text.split('\n') if line.strip()]
                                            
                                            # Look for substantive paragraphs (not navigation or headers)
                                            for line in lines:
                                                if len(line) > 50 and line not in processed_texts:
                                                    f.write(f"{line}\n\n")
                                                    processed_texts.add(line)
                                
                                elif article_resp.status_code == 429:  # Too Many Requests
                                    retry_count += 1
                                    if verbose:
                                        print(f"    Rate limited (429). Retry {retry_count}: waiting longer")
                                    time.sleep(5 + random.random() * 5)  # Wait 5-10 seconds
                                else:
                                    retry_count += 1
                                    if verbose:
                                        print(f"    Retry {retry_count}: Failed to access Article {article_num}, status code: {article_resp.status_code}")
                                    time.sleep(2 + random.random() * 3)  # Wait 2-5 seconds
                            except Exception as e:
                                retry_count += 1
                                if verbose:
                                    print(f"    Retry {retry_count}: Error processing Article {article_num}: {str(e)}")
                                time.sleep(2 + random.random() * 3)  # Wait 2-5 seconds
                        
                        # If we couldn't retrieve the article
                        if not article_retrieved:
                            if verbose:
                                print(f"    ERROR: Failed to retrieve Article {article_num} after {max_retries} attempts")
                            f.write(f"*Content could not be retrieved for Article {article_num}*\n\n")
                        
                        # Delay between article requests
                        if delay > 0:
                            jittered_delay = delay * (0.8 + 0.4 * random.random())  # 80-120% of specified delay
                            time.sleep(jittered_delay)
                else:
                    if verbose:
                        print(f"  ERROR: Failed to access Question {q_num}, status code: {response.status_code}")
                    f.write(f"*Content could not be retrieved for Question {q_num}*\n\n")
            except Exception as e:
                if verbose:
                    print(f"  ERROR: Exception when accessing Question {q_num}: {str(e)}")
                f.write(f"*Content could not be retrieved for Question {q_num} due to an error*\n\n")
            
            # Delay between question requests
            if delay > 0:
                jittered_delay = delay * (0.8 + 0.4 * random.random())  # 80-120% of specified delay
                time.sleep(jittered_delay)

        print(f"Scraping complete! Results saved to: {os.path.abspath(output_file)}")

# Example usage
if __name__ == "__main__":
    print("SUMMA THEOLOGICA SCRAPER")
    print("------------------------")

    # Get user input for scraping parameters
    output_file = input("Output file path [default: summa_output.txt]: ") or "summa_output.txt"
    
    part_options = {
        "1": "I",      # Prima Pars
        "2": "II-I",   # Prima Secundae
        "3": "II-II",  # Secunda Secundae
        "4": "III"     # Tertia Pars
    }
    
    print("\nSelect part of the Summa Theologica:")
    print("1. Part I (Prima Pars) - 119 questions")
    print("2. Part I-II (Prima Secundae) - 114 questions")
    print("3. Part II-II (Secunda Secundae) - 189 questions")
    print("4. Part III (Tertia Pars) - 90 questions")
    
    part_choice = input("Enter choice [default: 1]: ") or "1"
    part = part_options.get(part_choice, "I")
    
    default_end = get_default_end_question(part)
    
    start_q = int(input(f"\nStart from question # [default: 1]: ") or "1")
    end_q = int(input(f"End at question # [default: {default_end}]: ") or str(default_end))
    
    verbose = input("\nShow detailed progress? (y/n) [default: n]: ").lower() == 'y'
    delay = float(input("Delay between requests in seconds [default: 0]: ") or "0")
    
    # Run the scraper
    scrape_summa(output_file, part, start_q, end_q, delay, verbose)