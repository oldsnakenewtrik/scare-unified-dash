# SCARE Unified Metrics Dashboard Development Plan

Below is a structured software development plan for creating a unified metrics dashboard on Railway. This plan covers the entire lifecycle of the project and includes (seeded within it) the **actions needed to prepare disparate GitHub projects** for addition to the Railway environment.

---

## 1. **Project Overview & Objectives**

### 1.1 Goal
Create a single live—or twice-daily updating—dashboard that aggregates data from:
- **RedTrack**  
- **Matomo**  
- **Google Ads**  
- **Bing Ads**  
- **Salesforce** (via daily CSV report, no API access)

### 1.2 Primary Deliverables
1. A centralized data ingestion pipeline (including an email receiver service for Salesforce CSVs).  
2. A unified database hosted on [Railway](https://railway.app/) for all metrics.  
3. A single web-based dashboard (or set of micro front-end components) that displays all integrated metrics in near real-time/twice daily refreshes.  
4. Continuous integration/continuous deployment (CI/CD) for each GitHub project involved in the pipeline.  

---

## 2. **High-Level Architecture**

```
                +----------------+         +----------------+
                |  RedTrack     |         |  Matomo        |
                +-------+--------+         +----------------+
                        |                  
                        |  API Polling/ETL                
                        v                  
    +----------------------------+
    |    Data Ingestion Layer   | (Python/Node services)
    +----------------------------+
    |     Email Receiver for    | (Salesforce CSV)
    |     Salesforce CSV        |
    +------------+--------------+
                 |
         Clean & Transform
                 |
    +----------------------------+
    |  Central Database (Railway)|
    +------------+--------------+
                 |
        Frontend Dashboard (React/Vue/Next/etc.)
```

1. **Data Ingestion Layer**  
   - Polling APIs for Google Ads, Bing Ads, RedTrack, Matomo.  
   - Email receiver service for Salesforce CSV.  
   - Transform and store data.  

2. **Central Database** (Hosted on Railway)  
   - Stores unified metrics with schema that can be easily queried by the dashboard.  

3. **Frontend Dashboard**  
   - Reads from the central database.  
   - Possibly uses a single app or multiple micro front-ends that unify into one UI.  

---

## 3. **Detailed Plan & Action Items**

### 3.1 Phase 1: Requirements & Environment Setup

1. **Gather Requirements**  
   - Confirm required metrics from RedTrack, Matomo, Google Ads, Bing Ads, and Salesforce.  
   - Determine the update frequency (twice a day vs. real-time).  
   - Confirm data retention periods and data transformation logic.  

2. **Prepare GitHub Repositories**  
   - **Action**: Audit each existing GitHub project's structure, dependencies, and build scripts.  
   - **Action**: Add/Update each project's `Dockerfile` or relevant container configuration to ensure it can be deployed on Railway.  
     - For example, ensure that each service has:
       - A dedicated `Dockerfile`.  
       - A `requirements.txt` or `package.json` (depending on language) for easy dependency installation.  
       - A `Procfile` (if needed) or a custom entry command recognized by Railway.  

3. **Setup Railway Project**  
   - **Action**: Create a new Railway project (or identify an existing one).  
   - **Action**: Create a Railway plugin instance for a **PostgreSQL** or **MySQL** database (whichever suits your preference).  
   - **Action**: Prepare environment variables (API keys, tokens, etc.) in Railway's settings.  

4. **Define Data Model**  
   - **Action**: Create a schema for storing metrics from each source. For instance:
     - Table(s) for Ad metrics (Google Ads, Bing Ads).  
     - Table(s) for tracking data (RedTrack, Matomo).  
     - Table(s) for Salesforce metrics from CSV.  

### 3.2 Phase 2: Develop & Integrate Data Ingestion Services

#### 3.2.1 RedTrack & Matomo
- **Action**: Verify you have an API endpoint or method to retrieve data.  
- **Action**: In your chosen GitHub project for "Analytics Aggregation," create or update a service that:  
  - Schedules a job (e.g., using Cron or a scheduled trigger on Railway) to fetch data every 12 hours (or desired frequency).  
  - Stores that data into the central database.  
- **Action**: Prepare that service for deployment on Railway:
  - Add environment variables for RedTrack and Matomo API keys or credentials.  
  - Confirm that the project uses `Dockerfile` or another configuration recognized by Railway.  
  - If there is an existing GitHub repository, **create or update a CI/CD pipeline** (GitHub Actions or similar) to deploy automatically to Railway on new commits/tags.

#### 3.2.2 Google Ads & Bing Ads
- **Action**: Use the official Google Ads and Bing Ads SDKs (or RESTful APIs if that suits your language choice).  
- **Action**: In your "Ads Aggregation" GitHub repository (or create one if none exists):
  - Implement the data fetching logic with appropriate authentication.  
  - Provide transformations (e.g., converting currency, matching date/time formats).  
  - Store results in the central database.  
- **Action**: Test the pipeline locally with mock or test credentials.  
- **Action**: Containerize the project with a `Dockerfile`, ensuring it can run as a standalone service on Railway.  
- **Action**: Configure Cron (or scheduled tasks in Railway) for twice-daily pulls.

#### 3.2.3 Salesforce (Email to CSV Approach)
Because you do not have API access, you will:
1. **Action**: Set up an email receiver microservice (Node.js with `imap` or a serverless approach) in a dedicated GitHub repository. This service will:
   - Listen for incoming emails (via IMAP/POP3 or an email webhook) to a dedicated mailbox.  
   - Extract CSV attachments.  
   - Parse the CSV content.  
2. **Action**: Store the parsed CSV data into the central database.  
3. **Action**: Add environment variables in the project for:
   - Email host (IMAP/POP details).  
   - Email credentials (username/password).  
4. **Action**: Containerize this microservice with a `Dockerfile`.  

---

### 3.3 Phase 3: Data Transformation & Storage

1. **Data Normalization**  
   - Once the raw data is in your database (for each source), you may need additional transformations (e.g., consistent naming for "Spend," "Impressions," "Leads," etc.).  

2. **Database Schema Finalization**  
   - **Action**: Create a dedicated schema or set of normalized tables.  
   - **Action**: Possibly create summary or aggregate tables to speed up dashboard queries.  

3. **Backfill Historical Data**  
   - **Action**: Decide if you need to fetch historical data from these APIs or if you'll only handle new data forward. If historical data is needed, set up a one-time or a phased backfill.  

---

### 3.4 Phase 4: Unified Dashboard Development

1. **Front-End Framework**  
   - Choose your framework (React, Vue, Next.js, etc.).  
   - **Action**: Initialize a GitHub repository for the frontend dashboard.  

2. **API / Backend Gateway**  
   - **Action**: Create or extend an existing microservice to act as an API that the frontend can call to fetch aggregated metrics.  
   - This may involve writing queries that join data from RedTrack, Matomo, Google Ads, Bing Ads, and Salesforce.  

3. **Dashboard Components**  
   - **Action**: Implement chart components (e.g., Chart.js, D3.js, or another library).  
   - **Action**: Ensure each widget can auto-refresh based on the schedule or user-triggered refresh.  

4. **Deployment on Railway**  
   - **Action**: Create a `Dockerfile` or use a Node build process recognized by Railway for the front-end.  
   - **Action**: Configure environment variables for the front-end (e.g., base API URL).  

5. **CI/CD Integration**  
   - **Action**: Use GitHub Actions to deploy changes automatically to Railway when a pull request is merged or a commit is pushed to `main`/`master`.  

---

### 3.5 Phase 5: Monitoring, Logging, and Scheduling

1. **Set Up Cron or Scheduled Jobs**  
   - **Action**: Configure each microservice (data ingestion) to run twice daily or at specific intervals using Railway's Scheduler or an external Cron system.  

2. **Log Aggregation**  
   - **Action**: Ensure each microservice logs API responses, errors, and successful inserts.  
   - **Action**: Configure monitoring (DataDog, Sentry, or Railway logs) to track downtime or exceptions.  

3. **Alerting**  
   - **Action**: Set up notifications (Slack, email) if any data ingestion process fails.  

---

### 3.6 Phase 6: Testing & Validation

1. **Unit & Integration Tests**  
   - **Action**: Write tests for each microservice to ensure data is correctly fetched, transformed, and stored.  
   - **Action**: Test email attachments from Salesforce in a staging environment.  

2. **Performance & Load Testing**  
   - If data volumes are large, ensure the database can handle frequent writes and that the dashboard queries remain performant.  

3. **User Acceptance Testing**  
   - **Action**: Gather feedback from stakeholders using a test version of the dashboard.  
   - **Action**: Iterate based on feedback (display changes, new metrics, etc.).  

---

## 4. **Project Timeline (Example)**

| Phase                            | Duration (Weeks) | Key Milestones                              |
|----------------------------------|------------------|---------------------------------------------|
| **Phase 1: Requirements & Setup**| 1 - 2            | - GitHub repo audit <br> - Railway project & DB setup  |
| **Phase 2: Data Ingestion**      | 2 - 3            | - RedTrack/Matomo integration <br> - Google Ads & Bing Ads integration <br> - Email receiver for Salesforce |
| **Phase 3: Data Transformation** | 1 - 2            | - Database schema finalize <br> - Normalize & store data  |
| **Phase 4: Dashboard Dev**       | 2 - 4            | - Front-end build <br> - API endpoints <br> - Deployment to Railway |
| **Phase 5: Monitoring & Schedules** | 1 - 2         | - Cron jobs set <br> - Logging & alerting |
| **Phase 6: Testing & Launch**    | 1 - 2            | - Integration tests <br> - Stakeholder review <br> - Final launch |

---

## 5. **Next Steps & Conclusion**

1. **Immediate Next Steps**  
   - Organize each GitHub repository:
     - **Action**: Add/Update Dockerfiles.  
     - **Action**: Implement environment variable usage for config.  
     - **Action**: Add README instructions for local development and deployment to Railway.  
   - Finalize the data schema and create the necessary tables in the Railway-hosted database.  
   - Implement the email receiver microservice for Salesforce CSV ingestion.

2. **Long-Term Maintenance**  
   - Set up versioning and branching policies for the GitHub repos.  
   - Update the pipeline if new data sources are added in the future.  
   - Optimize dashboard queries as data volume grows.

By following this plan and preparing each GitHub project with proper containerization, environment variable handling, and CI/CD pipelines, you'll be able to **unify** all data sources (RedTrack, Matomo, Google Ads, Bing Ads, and Salesforce CSVs) into a **single metrics dashboard** hosted on Railway.
