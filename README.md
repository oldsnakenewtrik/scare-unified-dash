# SCARE Unified Metrics Dashboard

A centralized dashboard that aggregates and visualizes marketing metrics from multiple data sources, deployed on Railway.

## Project Overview

This project aims to create a unified dashboard that aggregates data from multiple marketing and analytics platforms:

- RedTrack
- Matomo
- Google Ads
- Bing Ads
- Salesforce (via CSV reports)

The dashboard provides a comprehensive view of marketing performance with automated data collection, transformation, and visualization.

## Architecture

The system consists of these main components:

1. **Data Ingestion Layer**: Services that collect data from various sources
   - API integrations for RedTrack, Matomo, Google Ads, and Bing Ads
   - Email receiver for Salesforce CSV reports

2. **Central Database**: PostgreSQL/MySQL database hosted on Railway

3. **Frontend Dashboard**: Web-based UI for data visualization

## Repository Structure

This repository will contain:

- Documentation
- Infrastructure configuration
- Deployment scripts
- Core components and services
- Database schema definitions

Individual data connector services may be maintained in separate repositories and deployed as microservices.

## Development Plan

See the [Development Plan](development-plan.md) for detailed implementation steps.

## Getting Started

### Prerequisites

- Railway account
- API access to RedTrack, Matomo, Google Ads, and Bing Ads
- Dedicated email account for receiving Salesforce CSV reports
- Docker and Docker Compose (for local development)

### Local Development

Instructions for local development will be added as the project progresses.

### Deployment

The project is designed to be deployed on [Railway](https://railway.app/), with each component containerized for easy deployment.

## Tech Stack

- **Backend**: Python/Node.js (for data ingestion services)
- **Database**: PostgreSQL/MySQL (hosted on Railway)
- **Frontend**: React/Vue/Next.js
- **Deployment**: Docker, Railway

## License

This project is proprietary and confidential.

## Contributing

Guidelines for contributing to this project will be established as development progresses.
