import asyncio
import csv
from datetime import datetime
import time
from random import randint

from twikit import Client, TooManyRequests
from configparser import ConfigParser

# Load credentials from config.ini
config = ConfigParser()
config.read('config.ini')
username = config['X']['username']
email = config['X']['email']
password = config['X']['password']

# Initialize the client
client = Client('en-US')

# CSV file setup
CSV_FILE = 'tweets.csv'
CSV_HEADERS = ['Tweet_count', 'Username', 'Text', 'Created_At', 'Tweet_ID']

# Search parameters - breaking down into ~10 day chunks
TIME_CHUNKS = [
    # 2024
    "until:2024-11-10 since:2024-11-01",
    "until:2024-11-20 since:2024-11-11",
    "until:2024-11-30 since:2024-11-21",
    "until:2024-12-10 since:2024-12-01",
    "until:2024-12-20 since:2024-12-11",
    "until:2024-12-31 since:2024-12-21",
    # 2025
    "until:2025-01-10 since:2025-01-01",
    "until:2025-01-13 since:2025-01-11"  # This last chunk covers the remaining days
]


async def fetch_tweets_for_period(client, base_query, time_period):
    """
    Fetches tweets for a specific time period
    """
    query = f"({base_query}) {time_period}"
    tweets = None
    results = []
    retries = 0
    max_retries = 3

    while True:
        try:
            if tweets is None:
                print(f"{datetime.now()} - Starting new search for period: {time_period}")
                tweets = await client.search_tweet(query, product="Latest")
            else:
                tweets = await tweets.next()

            if not tweets:
                print(f"{datetime.now()} - No more tweets for period: {time_period}")
                break

            for tweet in tweets:
                results.append(tweet)

            print(f"{datetime.now()} - Found {len(results)} tweets so far for period: {time_period}")
            # Add random delay between requests
            delay = randint(4, 8)
            print(f"Waiting {delay} seconds before next request...")
            await asyncio.sleep(delay)

        except TooManyRequests as e:
            rate_limit_reset = datetime.fromtimestamp(e.rate_limit_reset)
            wait_time = (rate_limit_reset - datetime.now()).total_seconds() + 15
            print(f"{datetime.now()} - Rate limit hit. Waiting {wait_time} seconds...")
            await asyncio.sleep(wait_time)
            continue

        except Exception as e:
            print(f"{datetime.now()} - Error: {e}")
            retries += 1
            if retries >= max_retries:
                print(f"{datetime.now()} - Max retries reached for period: {time_period}")
                break
            wait_time = 20 * retries  # Exponential backoff
            print(f"Retrying in {wait_time} seconds...")
            await asyncio.sleep(wait_time)
            continue

    return results


async def main():
    """
    Main function to scrape tweets using multiple time periods
    """
    try:
        # Login to Twitter
        print(f"{datetime.now()} - Logging in...")
        await client.login(auth_info_1=username, auth_info_2=email, password=password)
        print(f"{datetime.now()} - Login successful")

        tweet_count = 0
        base_query = "from:crypto"

        # Create or overwrite the CSV file with headers
        with open(CSV_FILE, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(CSV_HEADERS)

        # Iterate through each time period
        for time_period in TIME_CHUNKS:
            print(f"\n{datetime.now()} - Starting new period: {time_period}")

            tweets = await fetch_tweets_for_period(client, base_query, time_period)

            # Write tweets to CSV
            with open(CSV_FILE, 'a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                for tweet in tweets:
                    tweet_count += 1
                    tweet_data = [
                        tweet_count,
                        tweet.user.name,
                        tweet.text,
                        tweet.created_at,
                        tweet.id
                    ]
                    writer.writerow(tweet_data)

            print(f"{datetime.now()} - Completed period {time_period}. Found {len(tweets)} tweets")

            # Add longer delay between time periods
            delay = randint(20, 30)
            print(f"Waiting {delay} seconds before next time period...")
            await asyncio.sleep(delay)

        print(f'{datetime.now()} - Scraping completed! Total tweets found: {tweet_count}')

    except Exception as e:
        print(f'{datetime.now()} - A major error occurred: {e}')


if __name__ == "__main__":
    asyncio.run(main())