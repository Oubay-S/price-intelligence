# Apache NiFi Configuration Guide for Bigtable Ingestion

This guide provides the specific configuration details for the NiFi processors needed to automate the ingestion of scraped JSON files into your Bigtable emulator.

## 1. Processor: GetFile
*   **Purpose:** Monitors your project directories for new JSON files.
*   **Properties:**
    *   **Input Directory:** `/home/omar/Desktop/baaaaaaaaaaaaaaaaaaack-20260407T210643Z-3-001/baaaaaaaaaaaaaaaaaaack/projet_data_demo/`
    *   **File Filter:** `.*\.json`
    *   **Recursive Subdirectories:** `true`
    *   **Keep Source File:** `true` (Important: Keep it if you want the files to stay in the project, but you'll need to manage "already processed" files using a stateful processor or a different directory strategy).
    *   **Alternative:** Use `ListFile` -> `FetchFile` for better reliability in production.

## 2. Processor: SplitJson
*   **Purpose:** Breaks the JSON array (list of products) into individual JSON objects.
*   **Properties:**
    *   **JsonPath Expression:** `$.*` (This selects every element in the root array).

## 3. Processor: EvaluateJsonPath (Optional but recommended)
*   **Purpose:** Extracts fields like `name`, `price`, and `scraped_at` into FlowFile attributes.
*   **Properties:**
    *   **Destination:** `flowfile-attribute`
    *   **product_name:** `$.name`
    *   **product_category:** `$.category`

## 4. Processor: PutHBaseJSON
*   **Purpose:** Inserts the JSON record directly into Bigtable (using the HBase API compatibility).
*   **Properties:**
    *   **HBase Client Service:** (Create a new `HBase_2_ClientService`)
    *   **Table Name:** `products`
    *   **Row Identifier:** `${source}#${category}#${product_name:replaceAll('[^a-zA-Z0-9]', '')}` (Matches your Python row key logic).
    *   **Column Family:** `info`
    *   **Batch Size:** `100`

## 5. HBase Client Service Configuration
*   **Hadoop Configuration Files:** (You might need a minimal `hbase-site.xml` pointing to the emulator).
*   **Zookeeper Quorum:** `localhost`
*   **Zookeeper Client Port:** `8087` (Or wherever your Bigtable emulator is listening for HBase connections).

---

## 6. Handling Manual Interventions (Hybrid Workflow)

Since Walmart requires occasional CAPTCHA solving, follow this workflow:

1.  **Monitor Airflow:** If the `scrape_walmart` task fails or hits its timeout, it's likely a CAPTCHA or expired cookies.
2.  **Manual Cookie Refresh:** 
    *   Run `python3 walmart/generate_walmart_cookies.py` manually.
    *   Solve the CAPTCHA in the visible browser.
    *   Browsing for 10 seconds to establish trust.
    *   The script will save `walmart_cookies.json`.
3.  **Retry Task:** Go to the Airflow UI, click on the failed `scrape_walmart` task, and click **Clear** to retry it. It will now use the fresh cookies and should run automatically.

## Why use NiFi?
If you have NiFi running, you can disable the `load_to_bigtable` task in Airflow. NiFi will pick up files as soon as they are saved by the scrapers, making the data available in the dashboard even while other scrapers are still running! 

NiFi is also better at handling **data validation**. You can add a `ValidateRecord` processor to ensure that the JSON data saved by the scrapers is clean before it reaches Bigtable.
