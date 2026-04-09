# DWG to GIS Automation with Data Cleaning and Topology Control (ArcPy)

## Project Overview
This project develops an automated ArcPy workflow to convert DWG files into GIS features, addressing common issues such as data inconsistency, invalid geometries, and topology errors.

## Background
In real-world GIS workflows, CAD (DWG) data often contains inconsistent layers, missing attributes, and topology issues, making it difficult to use directly in GIS systems.

This project aims to automate the cleaning and conversion process to improve data usability and efficiency.

## Features
- Automated batch conversion from DWG to GIS feature classes
- Data cleaning for invalid geometries and redundant elements
- Topology validation with tolerance adjustment and error detection
- Improved robustness for processing multiple datasets

## Tech Stack
- ArcPy
- ArcGIS Pro

## Usage
1. Prepare DWG files in the input folder
2. Configure input/output paths in the script
3. Run the ArcPy script
4. Output GIS feature classes will be generated automatically
5. Topology validation results will be reported

Note: ArcGIS Pro environment is required.

## Results
- Successfully processed multiple real-world datasets
- Achieved stable topology validation results
- Identified and resolved common ArcGIS issues (e.g., data locking)

## Notes
This project focuses on practical GIS data processing and automation.
