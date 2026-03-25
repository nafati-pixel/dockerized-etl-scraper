# 🛒 MyTek RAM Price Tracker (Automated ETL Pipeline)

### 📖 The Business Case
Computer hardware pricing in Tunisia can be volatile and difficult to track. This project is a containerized **ETL (Extract, Transform, Load)** worker that automatically scrapes memory (RAM) prices and inventory status from MyTek.

By tracking this data over time and saving it to a relational database, it creates a historical pricing dataset that can be used to spot real discounts, track inflation, and identify restock patterns.

<img width="769" height="496" alt="Screenshot_2026-03-25_02-30-36" src="https://github.com/user-attachments/assets/c9b8fe89-af2e-4a86-a1fb-7e95f259a791" />


### 🏗️ The ETL Architecture
* **Extract:** Uses `Selenium` and `Selenium-Wire` to navigate MyTek's dynamic pages, intercepting network requests to reliably grab pricing and product data.
* **Transform:** Validates and sanitizes the scraped data using `Pydantic`, ensuring clean data types and stripping out currency strings (TND).
* **Load:** Uses `SQLAlchemy` and `Asyncpg` to asynchronously load the cleaned records directly into a PostgreSQL database.

### 🛠️ Tech Stack
* **Web Scraping:** Python, Selenium, Selenium-Wire
* **Data Validation:** Pydantic
* **Database & ORM:** PostgreSQL, SQLAlchemy, Psycopg2
* **Infrastructure:** Docker, Linux
  
<img width="1365" height="565" alt="Screenshot_2026-03-25_02-31-44" src="https://github.com/user-attachments/assets/ff0df739-989c-46ac-b998-2287b981f5bf" />


### 🚀 How to Run It Locally

Since this scraper runs inside a Docker container, you will need Docker installed and an accessible PostgreSQL database.

Clone the repository and enter the directory:

```bash
git clone [https://github.com/nafati-pixel/dockerized-etl-scraper.git](https://github.com/nafati-pixel/dockerized-etl-scraper.git)
cd dockerized-etl-scraper
