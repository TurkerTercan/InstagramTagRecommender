import json
import os
import re
import time
import pandas as pd
from random import random
from urllib.request import urlretrieve
from uuid import uuid4

from selenium.webdriver import Firefox
from selenium.webdriver.common.by import By
from webdriver_manager.firefox import GeckoDriverManager
from logger import get_logger, setup_logging


def get_posts(hashtag, n, browser, delay=5):
    """With the input of an account page, crawl the n most recent posts urls"""
    url = f"https://www.instagram.com/explore/tags/{hashtag}"
    browser.get(url)
    post = "https://www.instagram.com/p/"
    post_links = []
    images = []
    while len(post_links) < n or len(images) < n:
        img_src = [
            img.get_attribute("src") for img in browser.find_elements_by_css_selector("article img")
        ]
        links = [
            a.get_attribute("href") for a in browser.find_elements_by_tag_name("a")
        ]
        for link in links:
            if post in link and link not in post_links and len(post_links) < n:
                post_links.append(link)
        for image in img_src:
            if image not in images and len(images) < n:
                images.append(image)

        scroll_down = "window.scrollTo(0, document.body.scrollHeight);"
        browser.execute_script(scroll_down)
        time.sleep(1 + (random() * delay))

    return [
        {"post_link": post_links[i], "image": images[i], "search_hashtag": hashtag} for i in range(len(post_links))
    ]


def get_hashtags(url, browser):
    """Return a list of hashtags found in all post's comments"""
    browser.get(url)
    comments_html = browser.find_elements_by_css_selector("span")
    all_hashtags = []

    for comment in comments_html:
        hashtags = re.findall("#[A-Za-z]+", comment.text)
        if len(hashtags) > 0:
            all_hashtags.extend(hashtags)
    return list(set(all_hashtags))


def get_image(url, hashtag):
    """Download image from given url and return its name"""
    uuid = uuid4()
    urlretrieve(url, f"../../dataset/data/{hashtag}/{uuid}.jpg")
    name = f"{uuid}.jpg"
    return name


def crawl_data(hashtags, n, delay=5, hashtag_threshold=4):
    """Download n images and return a dictionary with their metadata"""
    setup_logging('crawl.txt', 'crawl')
    logger = get_logger('crawl')
    logger.info(f"Firefox started.")
    browser = Firefox(executable_path=GeckoDriverManager().install())
    browser.implicitly_wait(1)

    logger.info(f"Login to Instagram")
    browser.get('https://www.instagram.com')
    username_input = browser.find_element(By.CSS_SELECTOR, "input[name='username']")
    password_input = browser.find_element(By.CSS_SELECTOR, "input[name='password']")

    username_input.send_keys("your_username")
    password_input.send_keys("your_password")

    login_button = browser.find_element(By.XPATH, "//button[@type='submit']")
    login_button.click()
    time.sleep(20)

    logger.info(f"Trying to get {n} posts for each hashtag.")
    for hashtag in hashtags:
        logger.info(f"{hashtag} hashtag started.")
        posts = get_posts(hashtag, n, browser)
        try:
            os.mkdir(f"../../dataset/data/{hashtag}")
        except OSError as e:
            logger.info(e)

        logger.info(f"{len(posts)} has been crawled for #{hashtag}")
        counter = 0

        try:
            for post in posts:
                post["hashtags"] = get_hashtags(post["post_link"], browser)
                time.sleep(random() * delay)
                post["image_local_name"] = get_image(post["image"], hashtag)
                time.sleep(random() * delay)
                if len(post["hashtag"]) < hashtag_threshold:
                    posts.remove(post)
                else:
                    counter += 1
            new_hashtag_metadata = posts
        except Exception as e:
            print(e)
            new_hashtag_metadata = posts

        if os.path.exists(f"../../dataset/metadata/{hashtag}.json"):
            with open(f"../../dataset/metadata/{hashtag}.json", "r") as f:
                hashtag_metadata = json.load(f)
                hashtag_metadata += new_hashtag_metadata
        else:
            hashtag_metadata = new_hashtag_metadata

        with open(f"../../dataset/metadata/{hashtag}.json", "w") as f:
            json.dump(hashtag_metadata, f)
        logger.info(f"#{hashtag} is finished and {counter} suitable posts are found.")

