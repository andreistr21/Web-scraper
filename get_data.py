import time
import traceback
from multiprocessing import Pool
import csv
import logging

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException


logging.basicConfig(filename="main.log", level=logging.DEBUG, format="%(asctime)s:%(levelname)s:%(message)s")

max_wait_time = 10

options = webdriver.ChromeOptions()
# Headless mode
options.add_argument("--headless")
# Disable web driver mode
options.add_argument("--disable-blink-features=AutomationControlled")
# User-agent
options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36"
)
# Disable login
options.add_argument("--disable-logging")


def get_loaded(driver):
    try:
        name = (
            driver.find_element(By.CLASS_NAME, "align-items-end")
            .find_element(By.CSS_SELECTOR, 'h1[data-cmp="heading"]')
            .text
        )
    except NoSuchElementException:
        name = "N/A"
    try:
        price = driver.find_element(By.CLASS_NAME, "first-price").text
    except NoSuchElementException:
        price = "N/A"
    try:
        mileage = driver.find_element(By.CLASS_NAME, "margin-bottom-0").text[:-6]
    except NoSuchElementException:
        mileage = "N/A"

    try:
        VIN_n = driver.find_element(By.CLASS_NAME, "text-size-sm-500").text[6:23]
    except NoSuchElementException:
        VIN_n = "N/A"

    return name, price, mileage, VIN_n


def get_car_info_data(url):
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )

    try:
        driver.get(url)
        time.sleep(20)

        driver.execute_script("window.scrollTo(0, 1500)")
        time.sleep(1)

        failure_counter = 0
        name, price, mileage, VIN_n = None, None, None, None
        is_done = None
        while is_done is None:
            if failure_counter == 3:
                name, price, mileage, VIN_n = get_loaded(driver)
                break
            try:
                name = (
                    driver.find_element(By.CLASS_NAME, "align-items-end")
                    .find_element(By.CSS_SELECTOR, 'h1[data-cmp="heading"]')
                    .text
                )
                price = driver.find_element(By.CLASS_NAME, "first-price").text
                mileage = driver.find_element(By.CLASS_NAME, "margin-bottom-0").text[
                    :-6
                ]
                VIN_n = driver.find_element(By.CLASS_NAME, "text-size-sm-500").text[
                    6:23
                ]
                is_done = True
            except NoSuchElementException:
                failure_counter += 1
                time.sleep(5)
                driver.execute_script("window.scrollTo(0, 1500)")

        return url, name, price, mileage, VIN_n
    except Exception as e:
        print(e)
        print(traceback.format_exc())
    finally:
        driver.close()
        driver.quit()


def get_list_page_data(url, driver):
    driver.get(url)

    time.sleep(5)

    # Go through cars cards
    car_blocks_temp = WebDriverWait(driver, max_wait_time).until(
        EC.presence_of_all_elements_located(
            (By.CSS_SELECTOR, 'div[data-cmp="delayedImpressionWaypoint"]')
        )
    )
    car_blocks = car_blocks_temp[0:2] + car_blocks_temp[4:]

    # Get link for each car
    page_links = []
    for car_block in car_blocks:
        link = car_block.find_element(
            By.CSS_SELECTOR, 'a[rel="nofollow"]'
        ).get_attribute("href")
        page_links.append(link)

    pool = Pool(processes=int(len(page_links)))
    cars_info = pool.map(get_car_info_data, page_links)

    return cars_info


def get_next_page_url(driver, url, page_n):
    with open("index.html", "w") as file:
        file.write(driver.page_source)

    try:
        pagination = (
            driver.find_element(By.CLASS_NAME, "pagination")
            .find_element(By.CSS_SELECTOR, 'span[aria-label="Next"]')
            .find_element(By.XPATH, "..")
            .get_attribute("tabindex")
        )
        if pagination:
            return None
        else:
            return url + f"&firstRecord={page_n * 25}"
    except NoSuchElementException:
        return None


def get_data(url: str):
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )

    page_url = url
    page_n = 1
    cars_info = []
    try:
        while page_url is not None:
            try:
                logging.debug(page_url)
                cars_info += get_list_page_data(page_url, driver)
                page_url = get_next_page_url(driver, url, page_n)

                print(page_n)
                logging.debug(page_n)
                page_n += 1
                logging.debug(url)
                print(url)

            except Exception as e:
                print(e)
                print(traceback.format_exc())
                logging.debug(traceback.format_exc())
    finally:
        driver.close()
        driver.quit()

    return cars_info


def write_to_csv(cars_info):
    headers = ["Link", "Name", "Price ($)", "Mileage (miles)", "VIN_n"]

    with open("cars_info.csv", "w", newline="") as file:
        writer = csv.writer(file, delimiter=";")

        writer.writerow(headers)
        writer.writerows(cars_info)


def main():
    url = "https://www.autotrader.com/cars-for-sale/all-cars/nissan/altima/rochester-ny-14626?dma=&searchRadius=0&location=&marketExtension=include&startYear=2013&endYear=2018&trimCodeList=ALTIMA%7C3.5%20SL&isNewSearch=true&showAccelerateBanner=false&sortBy=relevance&numRecords=25"

    cars_info = get_data(url)

    write_to_csv(cars_info)


if __name__ == "__main__":
    main()
