import requests

def main():
    res = requests.get("https://www.goodreads.com/book/review_counts.json",
        params={"key":"KiCa5LTmht019IT2tHudCg", "isbns": "0765317508"})
    if res.status_code != 200:
        raise Exception("ERROR: API request unsuccessful.")
    data = res.json()
    review_count = data["books"][0]['reviews_count']
    average_rating = data['books'][0]['average_rating']
    print(data)
    print(review_count)
    print(average_rating)

if __name__ == "__main__":
    main()
