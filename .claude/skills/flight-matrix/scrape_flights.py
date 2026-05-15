import argparse
import time
import random
import pandas as pd
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import os

def get_driver():
    options = Options()
    # options.add_argument("--headless=new") # Run in headless mode
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as e:
        print(f"Error initializing driver: {e}")
        return None
    return driver

def construct_kayak_url(origin, dest, depart_date, return_date, passengers):
    dep_str = depart_date.strftime("%Y-%m-%d")
    ret_str = return_date.strftime("%Y-%m-%d")
    url = f"https://www.kayak.com/flights/{origin}-{dest}/{dep_str}/{ret_str}/{passengers}adults?sort=price_a"
    return url

def scrape_kayak(driver, url, passengers):
    try:
        driver.get(url)
        print(f"  Fetching {url}...")
        time.sleep(random.uniform(3, 6)) # More sleep to mimic human
        
        try:
             WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.CLASS_NAME, "resultWrapper"))
            )
        except Exception:
             print(f"  Timeout waiting for result wrapper (will try BS4 anyway)")
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        prices = []
        # Look for price elements containing '$'
        price_elements = soup.find_all(string=lambda text: text and '$' in text)
        
        for p_text in price_elements:
            clean_text = p_text.strip().replace('$', '').replace(',', '')
            if clean_text.isdigit():
                price = int(clean_text)
                if price > 200: # Filter out weird low numbers/ads
                     prices.append(price)
        
        if prices:
            best_per_person = min(prices)
            total_price = best_per_person * passengers
            print(f"  Best per-person price found: ${best_per_person}")
            return total_price
        
        return None

    except Exception as e:
        print(f"  Error: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Scrape flight prices matrix")
    parser.add_argument("--origin", required=True, help="Origin airport code (e.g., SLC)")
    parser.add_argument("--dest", required=True, help="Destination airport code (e.g., CDG)")
    parser.add_argument("--pax", type=int, default=1, help="Number of passengers")
    parser.add_argument("--start", required=True, help="Start date range for departure (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date range for departure (YYYY-MM-DD)")
    parser.add_argument("--min-days", type=int, default=7, help="Minimum trip duration (days)")
    parser.add_argument("--max-days", type=int, default=14, help="Maximum trip duration (days)")
    parser.add_argument("--output", default="flight_prices.csv", help="Output CSV file path")
    
    args = parser.parse_args()
    
    origin = args.origin.upper()
    dest = args.dest.upper()
    passengers = args.pax
    start_date = datetime.strptime(args.start, "%Y-%m-%d")
    end_date = datetime.strptime(args.end, "%Y-%m-%d")
    min_days = args.min_days
    max_days = args.max_days
    output_file = args.output

    driver = get_driver()
    if not driver:
        print("Failed to start driver")
        return

    results = []
    
    current_date = start_date
    while current_date <= end_date:
        # Calculate return window
        min_return = current_date + timedelta(days=min_days)
        max_return = current_date + timedelta(days=max_days)
        
        return_date = min_return
        while return_date <= max_return:
            
            print(f"Scraping: {current_date.date()} to {return_date.date()}")
            
            url = construct_kayak_url(origin, dest, current_date, return_date, passengers)
            price = scrape_kayak(driver, url, passengers)
            
            if price:
                print(f"  Found Total Price: ${price}")
                results.append({
                    "Depart": current_date.strftime("%Y-%m-%d"),
                    "Return": return_date.strftime("%Y-%m-%d"),
                    "Total_Price": price,
                    "Per_Person": price / passengers,
                    "Source": "Kayak"
                })
            else:
                print("  No price found or blocked")
            
            time.sleep(random.uniform(2, 4))
            return_date += timedelta(days=2) # Step 2 days to save time
        
        current_date += timedelta(days=2) # Step 2 days to save time

    driver.quit()
    
    if results:
        df = pd.DataFrame(results)
        df.to_csv(output_file, index=False)
        print(f"\nSaved results to {output_file}")
    else:
        print("\nNo results found.")

if __name__ == "__main__":
    main()
