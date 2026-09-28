# Cause of Death among People Experiencing Homelessness in Toronto

## Overview

This repo supports a paper that describes the recorded cause of death among people experiencing homelessness in Toronto, 2022 to 2024, using data published by Toronto Public Health through the City of Toronto Open Data Portal.


## File Structure

The repo is structured as:

-   `data/00-simulated_data` contains a simulated dataset used to test the analysis pipeline before the real data were obtained.
-   `data/01-raw_data` contains the raw "Homeless deaths by cause" resource as downloaded from the Open Data Portal.
-   `data/02-analysis_data` contains the cleaned dataset used in the paper.
-   `paper` contains the files used to generate the paper, including the Quarto document, the reference bibliography file, and the PDF of the paper.
-   `scripts` contains the scripts used to simulate, download, clean, and test the data.


## Scripts

Data acquisition is done in R, and simulation, cleaning, and testing are done in Python:

-   `00-simulate_data.py` simulates a dataset with the structure the real data are expected to have, before they are obtained.
-   `01-test_simulated_data.py` tests the simulated dataset against the distributions and totals it was generated from.
-   `02-download_data.R` downloads the raw data from the Open Data Portal using `opendatatoronto`.
-   `03-clean_data.py` cleans the raw data, flagging suppressed cells and converting counts to a usable format.
-   `04-test_analysis_data.py` tests the cleaned data against the raw file it was built from, checking schema, expected values, the suppression flag, and that cleaning did not change the underlying counts.


## Statement on LLM usage

Aspects of the code, writing, and plotting were done using the generative AI tool by Anthropic, Claude. The details of the usage can be found in other/llm_usage.