import time
import os
import shutil
import psutil
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException

def is_chrome_with_debug_port_running(port):
    """Check if Chrome is running with specific debug port using psutil."""
    for proc in psutil.process_iter(['name', 'cmdline']):
        try:
            if (proc.info['name'] == 'chrome.exe' and 
                f'--remote-debugging-port={port}' in ' '.join(proc.info['cmdline'] or [])):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return False

def launch_chrome():
    """Launch Chrome with debugging port and specific profile without closing other instances."""
    chrome_path = r'"C:\Program Files\Google\Chrome\Application\chrome.exe"'
    user_data_dir = r'"C:\Users\Chrome profile"'
    debugging_port = "9221"

    # Only launch if our specific debug instance isn't running
    if not is_chrome_with_debug_port_running(debugging_port):
        os.system(f'start "" {chrome_path} '
                f'--remote-debugging-port={debugging_port} '
                f'--user-data-dir={user_data_dir} '
                '--disable-background-timer-throttling '
                '--disable-renderer-backgrounding')

    time.sleep(5)  # Allow Chrome to launch

def connect_to_chrome():
    """Connect Selenium to existing Chrome session with profile verification."""
    debugging_port = "9221"
    expected_profile = r'C:\Users\Chrome profile'

    opt = Options()
    opt.add_experimental_option("debuggerAddress", f"localhost:{debugging_port}")
    opt.add_argument('--disable-background-timer-throttling')
    opt.add_argument('--disable-renderer-backgrounding')
    
    try:
        driver = webdriver.Chrome(options=opt)
        # Verify we're connected to the right profile
        if 'chrome' in driver.capabilities and 'userDataDir' in driver.capabilities['chrome']:
            if expected_profile not in driver.capabilities['chrome']['userDataDir']:
                driver.quit()
                raise Exception("Could not connect to the correct Chrome profile. Please ensure no other debug Chrome instances are running.")
        return driver
    except Exception as e:
        print(f"Connection failed: {e}")
        raise

def wait_for_element(driver, by, value, timeout=20):
    """Helper function for explicit waits."""
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, value))
    )

def adjust_browser_zoom(driver, zoom_level):
    """Set browser zoom level using JavaScript."""
    driver.execute_script(f"document.body.style.zoom='{zoom_level}%'")

def rename_downloaded_file(download_folder):
    """Rename the latest 'PH_Tracker_' file to include timestamp."""
    time.sleep(5)  # Allow time for download to start

    now = datetime.now()
    formatted_time = now.strftime("%m-%d-%Y_%H-%M")

    for _ in range(10):  # Retry for up to 10 seconds
        files = [f for f in os.listdir(download_folder) if f.startswith("PH_Tracker_") and not f.endswith(".crdownload")]
        if files:
            latest_file = max(files, key=lambda f: os.path.getctime(os.path.join(download_folder, f)))
            old_path = os.path.join(download_folder, latest_file)
            new_filename = f"PH_Tracker_{formatted_time}.csv"
            new_path = os.path.join(download_folder, new_filename)

            shutil.move(old_path, new_path)
            print(f"Renamed file to: {new_filename}")
            return
        time.sleep(1)

    print("No new file found for renaming.")

def reset_filters(driver, filter_name):
    """Enhanced filter reset with better waiting."""
    try:
        print(f"Resetting {filter_name} filter...")
        filter_button = wait_for_element(driver, By.XPATH, f"//button[contains(@data-automation-context, '{filter_name}')]", 15)
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", filter_button)
        driver.execute_script("arguments[0].click();", filter_button)
        
        reset_option = wait_for_element(driver, By.XPATH, "//li[contains(@data-automation-id, 'sheet_control_reset')]", 10)
        driver.execute_script("arguments[0].click();", reset_option)
        
        print(f"Successfully reset {filter_name} filter")
        time.sleep(1)  # Allow filter to apply

    except Exception as e:
        print(f"Warning: Could not reset {filter_name} filter - {str(e)}")

def run_dashboard_operations(driver):
    """Perform operations on the dashboard and download data."""
    download_folder = r"C:\Users\Downloads"
    dashboard_url = "https:///dashboards"

    driver.get(dashboard_url)
    
    try:
        # Wait for page to load completely
        wait_for_element(driver, By.XPATH, "//span[text()='PH Tracker &  Sessions Report']", 30)
        
        print("CloudWatch dashboard loaded successfully")

        # Activate the correct tab
        tab = wait_for_element(driver, By.XPATH, "//span[text()='PH Tracker &  Sessions Report']")
        driver.execute_script("arguments[0].click();", tab)
        print("Activated PH Tracker & Sessions Report tab")

        # Adjust zoom level
        adjust_browser_zoom(driver, 50)
        print("Adjusted browser zoom level")

        # Reset filters
        reset_filters(driver, "Associate")
        reset_filters(driver, "Manager")
        reset_filters(driver, "Job type")
        reset_filters(driver, "Site")

        # Scroll to and click the element
        element = wait_for_element(driver, By.XPATH, "(//div[contains(@class,'visual-title-container')])[2]")
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
        driver.execute_script("arguments[0].click();", element)
        time.sleep(1)

        # Export data
        menu_button = wait_for_element(driver, By.XPATH, "//button[@aria-label='Menu options, PH Tracker, Table']")
        driver.execute_script("arguments[0].click();", menu_button)
        
        export_option = wait_for_element(driver, By.XPATH, "//li[contains(@data-automation-id,'dashboard_visual_dropdown_export')]")
        driver.execute_script("arguments[0].click();", export_option)

        rename_downloaded_file(download_folder)

    except Exception as e:
        print(f"Error during dashboard operations: {str(e)}")
        raise

def main():
    try:
        interval = float(input("Enter the time interval in minutes: ")) * 60
        num_runs = int(input("Enter the number of times to run the script: "))
        print(f"Script will run {num_runs} times every {interval / 60} minutes. Press Ctrl+C to stop earlier.")

        launch_chrome()
        driver = connect_to_chrome()

        run_count = 0
        while run_count < num_runs:
            print(f"\nRun {run_count + 1} of {num_runs}")
            try:
                run_dashboard_operations(driver)
                run_count += 1
            except Exception as e:
                print(f"An error occurred: {e}")
                print("Reconnecting to Chrome...")
                driver = connect_to_chrome()
            print(f"Operations completed. Waiting {interval / 60} minutes before next run...")
            time.sleep(interval)

        print("Script completed the specified number of runs.")

    except KeyboardInterrupt:
        print("\nScript stopped by user.")
    except ValueError:
        print("Please enter a valid number for the interval and number of runs.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    finally:
        if 'driver' in locals() and driver:
            driver.quit()

if __name__ == "__main__":
    main()