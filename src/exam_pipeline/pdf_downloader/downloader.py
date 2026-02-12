"""PDF downloader for Korean exam files from comcbt.com."""

import logging
import re
import time
from pathlib import Path
from typing import Callable, List, Optional, Tuple

import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logger = logging.getLogger(__name__)


class PDFDownloadError(Exception):
    """PDF download errors."""

    pass


class PDFDownloader:
    """
    Downloads Korean exam PDFs from comcbt.com using Selenium.

    Scrapes board listings for (교사용).pdf files and organizes them by category.
    """

    # URL patterns to exclude from scraping
    EXCLUDE_PATTERNS = [
        r"dispMemberLoginForm",
        r"dispMemberSignUpForm",
        r"dispMemberFindAccount",
        r"index\.php\?mid=imsigongsi&act=",
        r"index\.php\?module=lottery",
        r"webhaesul",
        r"^//",
        r"#",
        r"^https?://m\.comcbt\.com/",
    ]

    def __init__(
        self,
        download_dir: Path,
        max_pdfs_per_category: int = 15,
        request_timeout: int = 20,
        implicit_wait: int = 3,
    ):
        """
        Initialize PDF downloader.

        Args:
            download_dir: Base directory for downloads
            max_pdfs_per_category: Maximum PDFs to download per category (default: 15)
            request_timeout: HTTP request timeout in seconds
            implicit_wait: Selenium implicit wait in seconds
        """
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)

        self.max_pdfs_per_category = max_pdfs_per_category
        self.request_timeout = request_timeout
        self.implicit_wait = implicit_wait

        self.driver: Optional[WebDriver] = None
        self._compiled_patterns = [re.compile(p) for p in self.EXCLUDE_PATTERNS]

    def _is_excluded(self, url: str) -> bool:
        """Check if URL matches any exclude pattern."""
        if not url:
            return True
        for pattern in self._compiled_patterns:
            if pattern.search(url):
                return True
        return False

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """Remove invalid characters from filename."""
        return re.sub(r'[\\/:*?"<>|]', "_", filename)

    @staticmethod
    def _extract_category_name(filename: str) -> str:
        """
        Extract category name from PDF filename.

        Example:
            "산업안전기사20230401(교사용).pdf" → "산업안전기사"
        """
        name = re.sub(r"\(교사용\)\.pdf$", "", filename)
        name = re.sub(r"\d{11}", "", name)  # Remove 11-digit numbers
        name = re.sub(r"\d+", "", name)  # Remove all remaining digits
        return PDFDownloader._sanitize_filename(name.strip())

    def _init_driver(self) -> None:
        """Initialize Chrome WebDriver with anti-detection options."""
        try:
            logger.info("Initializing ChromeDriver...")

            # Configure Chrome options for stealth
            options = webdriver.ChromeOptions()
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)

            service = Service()
            self.driver = webdriver.Chrome(service=service, options=options)

            # Hide webdriver property
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

            self.driver.implicitly_wait(self.implicit_wait)
            logger.info("ChromeDriver initialized successfully")
        except Exception as e:
            raise PDFDownloadError(
                f"Failed to initialize ChromeDriver: {e}\n"
                "Make sure Chrome browser is installed."
            )

    def _close_driver(self) -> None:
        """Close Chrome WebDriver."""
        if self.driver:
            self.driver.quit()
            self.driver = None
            logger.info("ChromeDriver closed")

    def _dismiss_modals(self, ad_wait_time: int = 15) -> None:
        """
        Attempt to dismiss any popup modals or ads.

        Strategy: Wait for ad viewing time, then click close button.

        Args:
            ad_wait_time: Seconds to wait before attempting to close ad (default: 15)
        """
        if not self.driver:
            return

        modal_dismissed = False

        # Strategy 1: Check for ad modal and wait before closing
        try:
            # Look for the "Unlock more content" or ad modal
            unlock_text_elements = self.driver.find_elements(
                By.XPATH, "//*[contains(text(), 'Unlock more content')]"
            )

            if unlock_text_elements:
                logger.info(f"Detected ad modal, waiting {ad_wait_time} seconds before closing...")
                time.sleep(ad_wait_time)

                # Now try to find and click the close button
                close_selectors = [
                    # X button patterns (most common for ads)
                    "button[aria-label='Close']",
                    "button[title='닫기']",
                    "a[title='닫기']",
                    # Close button with icon
                    "button.close",
                    "button.btn-close",
                    "a.close",
                    # Generic patterns
                    "button[class*='close']",
                    "a[class*='close']",
                    "svg[class*='close']",
                    # Modal specific
                    ".modal-close",
                    ".popup-close",
                    ".ad-close",
                ]

                for selector in close_selectors:
                    try:
                        wait = WebDriverWait(self.driver, 2)
                        close_button = wait.until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                        close_button.click()
                        logger.info(f"Closed ad modal using selector: {selector}")
                        modal_dismissed = True
                        time.sleep(1)  # Wait for modal to close
                        break
                    except (TimeoutException, NoSuchElementException):
                        continue
                    except Exception as e:
                        logger.debug(f"Error with selector {selector}: {e}")
                        continue

                # If close button not found, try ESC key as fallback
                if not modal_dismissed:
                    try:
                        actions = ActionChains(self.driver)
                        actions.send_keys(Keys.ESCAPE).perform()
                        logger.info("Closed ad modal using ESC key")
                        modal_dismissed = True
                        time.sleep(1)
                    except Exception as e:
                        logger.debug(f"ESC key failed: {e}")

                return  # Exit early if we handled the ad modal

        except Exception as e:
            logger.debug(f"Ad modal detection failed: {e}")

        # Strategy 2: Quick check for other modals (non-ad popups)
        # These can be closed immediately without waiting
        close_selectors = [
            "button.close",
            "button.btn-close",
            ".modal-close",
            ".popup-close",
        ]

        for selector in close_selectors:
            try:
                wait = WebDriverWait(self.driver, 1)
                close_button = wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                )
                close_button.click()
                logger.info(f"Dismissed non-ad modal using selector: {selector}")
                modal_dismissed = True
                time.sleep(0.5)
                break
            except (TimeoutException, NoSuchElementException):
                continue
            except Exception as e:
                logger.debug(f"Error with selector {selector}: {e}")
                continue

        # Strategy 3: Handle iframes
        try:
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            if iframes:
                logger.debug(f"Found {len(iframes)} iframes")
                # Switch back to main content in case we're in an iframe
                self.driver.switch_to.default_content()
        except Exception as e:
            logger.debug(f"Error handling iframes: {e}")

        if not modal_dismissed:
            logger.debug("No modal detected or already dismissed")

    def _download_file(self, file_url: str, save_path: Path) -> bool:
        """Download file from URL using HTTP GET."""
        if save_path.exists():
            logger.info(f"File already exists, skipping: {save_path.name}")
            return True

        logger.info(f"Downloading: {save_path.name}")

        try:
            response = requests.get(file_url, timeout=self.request_timeout)
            response.raise_for_status()

            with open(save_path, "wb") as f:
                f.write(response.content)

            logger.info(f"✓ Downloaded: {save_path.name}")
            return True

        except Exception as e:
            logger.error(f"✗ Download failed: {e}")
            return False

    def download_from_board(
        self,
        board_url: str,
        exam_title: str = "",
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> Tuple[Optional[Path], int]:
        """
        Download PDFs from a single board URL.

        Args:
            board_url: URL of the exam category board
            exam_title: Title of exam (for logging)
            log_callback: Optional callback for progress logging

        Returns:
            Tuple of (category_folder, files_downloaded)
        """
        if not self.driver:
            self._init_driver()

        if self._is_excluded(board_url):
            logger.info(f"Skipping excluded URL: {board_url}")
            return None, 0

        logger.info(f"Visiting board: {board_url}")
        if log_callback:
            log_callback(f"Visiting: {exam_title or board_url}")

        self.driver.get(board_url)
        time.sleep(1)

        # Dismiss any popup modals or ads
        self._dismiss_modals()

        # Extract post links from board table
        post_links_data = []
        try:
            post_links = self.driver.find_elements(
                By.CSS_SELECTOR, "table tbody tr td:nth-child(2) a"
            )

            for link_elem in post_links:
                href = link_elem.get_attribute("href")
                text = link_elem.text.strip()
                if href and not self._is_excluded(href):
                    post_links_data.append((href, text))

        except Exception as e:
            logger.error(f"Failed to extract post links: {e}")
            return None, 0

        if not post_links_data:
            logger.info(f"No posts found at: {board_url}")
            if log_callback:
                log_callback("No posts found on this board")
            return None, 0

        logger.info(f"Found {len(post_links_data)} posts")
        if log_callback:
            log_callback(f"Found {len(post_links_data)} posts, checking for PDFs...")

        category_folder: Optional[Path] = None
        files_downloaded = 0

        # Limit to max_pdfs_per_category posts
        posts_to_check = min(len(post_links_data), self.max_pdfs_per_category)

        for idx, (post_href, post_text) in enumerate(
            post_links_data[:posts_to_check], start=1
        ):
            logger.info(f"[{idx}/{posts_to_check}] Checking: {post_text[:50]}")
            if log_callback:
                log_callback(f"[{idx}/{posts_to_check}] {post_text[:50]}...")

            try:
                # Add random delay to appear more human-like
                import random
                time.sleep(random.uniform(1.5, 2.5))

                self.driver.get(post_href)
                time.sleep(random.uniform(0.8, 1.5))

                # Dismiss any popup modals or ads
                self._dismiss_modals()

                # Find attachment links
                attach_links = self.driver.find_elements(
                    By.CSS_SELECTOR, "div.rd_body.clear article div p a"
                )

                found_pdf = False
                for a_elem in attach_links:
                    fname = a_elem.text.strip()
                    href = a_elem.get_attribute("href")

                    if "(교사용).pdf" in fname and href:
                        found_pdf = True

                        # Create category folder on first PDF found
                        if category_folder is None:
                            category_name = self._extract_category_name(fname)
                            category_folder = self.download_dir / category_name
                            category_folder.mkdir(parents=True, exist_ok=True)
                            logger.info(f"Created category folder: {category_folder}")
                            if log_callback:
                                log_callback(f"Category: {category_name}")

                        local_path = category_folder / self._sanitize_filename(fname)
                        if self._download_file(href, local_path):
                            files_downloaded += 1
                            if log_callback:
                                log_callback(
                                    f"  ✓ Downloaded ({files_downloaded}/{posts_to_check})"
                                )

                            # Stop if we've reached our target
                            if files_downloaded >= self.max_pdfs_per_category:
                                logger.info(
                                    f"Reached target: {files_downloaded} PDFs"
                                )
                                break
                        break

                if not found_pdf:
                    logger.debug(f"No (교사용).pdf found in: {post_text}")

            except Exception as e:
                error_msg = str(e)
                logger.warning(f"Error processing post: {error_msg}")

                # If session is invalid, try to recover
                if "invalid session id" in error_msg.lower():
                    logger.error("Session lost, attempting to reinitialize driver")
                    try:
                        self._close_driver()
                        self._init_driver()
                        logger.info("Driver reinitialized, continuing...")
                        # Skip to next post after recovery
                    except Exception as recovery_error:
                        logger.error(f"Failed to recover: {recovery_error}")
                        break
                continue

            # Break outer loop if we've hit our target
            if files_downloaded >= self.max_pdfs_per_category:
                break

        logger.info(f"Download complete: {files_downloaded} files")
        if log_callback:
            log_callback(f"\n✓ Downloaded {files_downloaded} PDF files")

        return category_folder, files_downloaded

    def download_exam_category(
        self,
        board_url: str,
        exam_title: str = "",
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> Tuple[bool, Optional[Path], int]:
        """
        Download exam PDFs from a category board (with automatic driver management).

        Args:
            board_url: URL of exam category board
            exam_title: Title of exam (for logging)
            log_callback: Optional callback for progress logging

        Returns:
            Tuple of (success, category_folder, files_downloaded)
        """
        try:
            self._init_driver()
            folder, count = self.download_from_board(board_url, exam_title, log_callback)
            return True, folder, count

        except Exception as e:
            logger.error(f"Download failed: {e}")
            if log_callback:
                log_callback(f"Error: {e}")
            return False, None, 0

        finally:
            self._close_driver()


def download_exam_pdfs(
    board_url: str,
    download_dir: Path,
    exam_title: str = "",
    max_pdfs: int = 15,
    log_callback: Optional[Callable[[str], None]] = None,
) -> Tuple[bool, Optional[Path], int]:
    """
    Convenience function for downloading exam PDFs.

    Args:
        board_url: URL of exam category board
        download_dir: Directory to save PDFs
        exam_title: Title of exam (for logging)
        max_pdfs: Maximum number of PDFs to download (default: 15)
        log_callback: Optional callback for progress logging

    Returns:
        Tuple of (success, category_folder, files_downloaded)
    """
    downloader = PDFDownloader(download_dir, max_pdfs_per_category=max_pdfs)
    return downloader.download_exam_category(board_url, exam_title, log_callback)
