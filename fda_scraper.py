#!/usr/bin/env python
# coding: utf-8

# Import and install necessary packages.
import subprocess
import sys

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

install("bs4")
install("requests")
install("pandas")
install("regex")

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re

# Helper function that returns a Classification Product Code (CPC) when passed an appropriately formatted HTML element.
# Replaces some repetitious code in the scraping loop.
def get_cpc(cpc_label):
    cpc_element = cpc_label.parent.parent
    cpc_code_element = cpc_element.find("a")
    cpc = cpc_code_element.text[-3:]
    return cpc

# Create BeautifulSoup object from FDA Nucleic Acid Based Tests webpage.
URL = "https://www.fda.gov/medical-devices/in-vitro-diagnostics/nucleic-acid-based-tests"
page = requests.get(URL)
soup = BeautifulSoup(page.content, "html.parser")

# Find table of human tests within webpage and then find all test listings as individual elements.
human_test_table = soup.find(summary = "List of Human Genetic Tests")
human_tests = human_test_table.find_all("tr")

# Instantiate a few variables based on setup of human tests table. Avoids a few magic numbers in code.
fields_left = 0
num_fields = 4
trade_name_alignment = num_fields - 4
submission_alignment = num_fields - 3

# Instantiate table to hold output.
human_tests_df = pd.DataFrame(columns = ['disease_use', 'trade_name', 'submission', 'url_of_c', 'cpc'])

# Scraping loop.
for test in human_tests:
    
    #Find all HTML objects associated with fields (Trade Name, Manufacturer, etc.) for a given test listing.
    fields = test.find_all("td")
    for field in fields:
        
        # For each field, test to see what type of field it is with the help of field counter variable
        # and store the field's value in the appropriate variable. 
        # Since trade name field sometimes spans many rows, we keep track of how many have passed.
        if fields_left == 0:
            if field.text.strip() != '':
                disease_use = field.text.strip()
            if field.has_attr("rowspan"):
                rowspan = int(field["rowspan"])
            else:
                rowspan = 1
            fields_left = rowspan * (num_fields - 1) + 1
        elif fields_left % (num_fields - 1) == trade_name_alignment:
            trade_name = field.text.strip()
        elif fields_left % (num_fields - 1) == submission_alignment:
            
            # If field is submission field, loop through all submissions and their respective links.
            submissions = field.find_all("a")
            for submission_element in submissions:
                submission = submission_element.text.strip()
                url_of_c = submission_element["href"]
                cpc = ""
                
                # Test whether submission link is broken. If so, create entry without CPC and 
                # proceed to next submission.
                try:
                    product_page = requests.get(url_of_c)
                except:
                    continue
                else:
                    
                    # If submission link is not broken, create new BeautifulSoup object to scrape
                    # using submission link URL and then scrape CPC.
                    product_soup = BeautifulSoup(product_page.content, "html.parser")
                    cpc_label = product_soup.find(string = lambda text: "Product Code" in text)
                    
                    # If there is no CPC listing on submission link page, check for additional
                    # links to explore. Some pages require clicking down one more level before
                    # CPC is provided.
                    if cpc_label is None:
                        sublinks = product_soup.find_all(style="text-decoration:underline;")
                        if sublinks is not None:
                            for link in sublinks:
                                sublink_url = "https://www.accessdata.fda.gov" + link["href"]
                                try:
                                    sublink_page = requests.get(sublink_url)
                                except:
                                    continue
                                else:
                                    sublink_soup = BeautifulSoup(sublink_page.content, "html.parser")
                                    cpc_label = sublink_soup.find(string = lambda text: "Product Code" in text)
                                    cpc = get_cpc(cpc_label)
                                    break
                    else:
                        cpc = get_cpc(cpc_label)
                finally:
                    new_row_df = pd.DataFrame({'disease_use' : disease_use, 
                                               'trade_name' : trade_name, 
                                               'submission' : submission,
                                               'url_of_c' : url_of_c,
                                               'cpc' : cpc},
                                             index = [0])
                    human_tests_df = pd.concat([human_tests_df, new_row_df], ignore_index = True, axis = 0)
        fields_left -= 1

# Save output to CSV.
human_tests_df.to_csv('human_tests.csv')
