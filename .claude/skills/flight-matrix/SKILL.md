---
name: flight-matrix
description: Generate flight price matrices by scraping live pricing data when APIs are unavailable or too expensive.
---

# flight-matrix

Generate a price matrix for flights using automated scraping (Kayak) when APIs are unavailable or expensive.

## Description

This skill spawns a Python script that uses Selenium (headless Chrome) to scrape flight prices for a range of dates and passenger counts. It outputs a CSV file with the best price found for each date combination.

## Usage

`python3 scrape_flights.py --origin SLC --dest CDG --start 2026-07-16 --end 2026-07-31 --pax 5`

## Arguments

- `--origin`: Origin airport code (e.g., SLC)
- `--dest`: Destination airport code (e.g., CDG)
- `--start`: Start date for departure window (YYYY-MM-DD)
- `--end`: End date for departure window (YYYY-MM-DD)
- `--pax`: Number of passengers (default: 1)
- `--min-days`: Minimum trip duration in days (default: 7)
- `--max-days`: Maximum trip duration in days (default: 14)
- `--output`: Output CSV filename (default: flight_prices.csv)
