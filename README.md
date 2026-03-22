# MyTek RAM Price Tracker (Automated ETL Pipeline)

## 📖 The Business Case
Computer hardware pricing in Tunisia can be volatile and difficult to track. This project is a containerized ETL (Extract, Transform, Load) worker that automatically scrapes memory (RAM) prices and inventory status from MyTek. 

By tracking this data over time and saving it to a relational database, it creates a historical pricing dataset that can be used to spot real discounts, track inflation, and identify restock patterns.

## 🏗️ The ETL Architecture
* **Extract:** Uses **Selenium** and **Selenium-Wire** to navigate MyTek's dynamic pages, intercepting network requests to reliably grab pricing and product data.
* **Transform:** Validates and sanitizes the scraped data using **Pydantic**, ensuring clean data types and stripping out currency strings (TND).
* **Load:** Uses **SQLAlchemy** and **Asyncpg** to asynchronously load the cleaned records directly into a **PostgreSQL** database.

## 🛠️ Tech Stack
* **Web Scraping:** Python, Selenium, Selenium-Wire
* **Data Validation:** Pydantic
* **Database & ORM:** PostgreSQL, SQLAlchemy, Psycopg2
* **Infrastructure:** Docker

## 🚀 How to Run It Locally
Since this scraper runs inside a Docker container, you will need Docker installed and an accessible PostgreSQL database.

1. Clone the repository:
   ```bash
   git clone [https://github.com/nafati-pixel/dockerized-etl-scraper.git](https://github.com/nafati-pixel/dockerized-etl-scraper.git)
   cd dockerized-etl-scraper
