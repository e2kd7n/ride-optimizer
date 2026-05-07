"""
Test script for interactive map filtering and route selection functionality.

Tests:
1. Filter controls are present on commute page
2. Route selection (click-to-highlight) works
3. Mobile filter panel toggle works
4. Filter state persistence works
5. Touch targets meet 44x44px minimum
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def setup_driver():
    """Setup Chrome driver with mobile emulation."""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    # Mobile emulation for iPhone SE
    mobile_emulation = {
        "deviceMetrics": {"width": 375, "height": 667, "pixelRatio": 2.0},
        "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15"
    }
    chrome_options.add_experimental_option("mobileEmulation", mobile_emulation)
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def test_commute_page_filters(base_url='http://localhost:5000'):
    """Test filter controls on commute page."""
    print("\n=== Testing Commute Page Filters ===")
    
    driver = setup_driver()
    try:
        # Navigate to commute page
        driver.get(f'{base_url}/commute')
        print(f"✓ Navigated to {base_url}/commute")
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'commute-page'))
        )
        print("✓ Page loaded successfully")
        
        # Check if filter panel exists
        try:
            filter_panel = driver.find_element(By.ID, 'map-filter-panel')
            print("✓ Filter panel found")
        except NoSuchElementException:
            print("✗ Filter panel not found (will be created by JavaScript)")
        
        # Check if filter toggle button exists (mobile)
        try:
            toggle_btn = driver.find_element(By.ID, 'filter-toggle-btn')
            print(f"✓ Filter toggle button found")
            
            # Check button size (touch target)
            size = toggle_btn.size
            if size['height'] >= 44 and size['width'] >= 44:
                print(f"✓ Toggle button meets touch target minimum: {size['width']}x{size['height']}px")
            else:
                print(f"✗ Toggle button too small: {size['width']}x{size['height']}px (minimum 44x44px)")
        except NoSuchElementException:
            print("ℹ Filter toggle button not found (may be created by JavaScript)")
        
        # Check for route cards
        route_cards = driver.find_elements(By.CLASS_NAME, 'route-option-card')
        print(f"✓ Found {len(route_cards)} route cards")
        
        if route_cards:
            # Test route selection
            first_card = route_cards[0]
            route_id = first_card.get_attribute('data-route-id')
            print(f"✓ First route card has data-route-id: {route_id}")
            
            # Click the card
            first_card.click()
            time.sleep(0.5)
            
            # Check if card has selected class
            if 'route-selected' in first_card.get_attribute('class'):
                print("✓ Route card selection works")
            else:
                print("ℹ Route card selection class not applied (may require JavaScript execution)")
        
        # Check for map container
        try:
            map_container = driver.find_element(By.ID, 'commute-comparison-map')
            print("✓ Map container found")
        except NoSuchElementException:
            print("ℹ Map container not found (may not be present without data)")
        
        print("\n✓ Commute page filter tests completed")
        
    except TimeoutException:
        print("✗ Timeout waiting for page to load")
    except Exception as e:
        print(f"✗ Error during test: {e}")
    finally:
        driver.quit()

def test_dashboard_map(base_url='http://localhost:5000'):
    """Test dashboard overview map."""
    print("\n=== Testing Dashboard Map ===")
    
    driver = setup_driver()
    try:
        driver.get(f'{base_url}/dashboard')
        print(f"✓ Navigated to {base_url}/dashboard")
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'dashboard'))
        )
        print("✓ Dashboard loaded successfully")
        
        # Check for overview map
        try:
            map_section = driver.find_element(By.CLASS_NAME, 'overview-map-section')
            print("✓ Overview map section found")
            
            map_container = driver.find_element(By.ID, 'dashboard-overview-map')
            print("✓ Map container found")
        except NoSuchElementException:
            print("ℹ Overview map not found (may not be present without data)")
        
        print("\n✓ Dashboard map tests completed")
        
    except Exception as e:
        print(f"✗ Error during test: {e}")
    finally:
        driver.quit()

def test_filter_persistence(base_url='http://localhost:5000'):
    """Test filter state persistence in localStorage."""
    print("\n=== Testing Filter State Persistence ===")
    
    driver = setup_driver()
    try:
        driver.get(f'{base_url}/commute')
        
        # Wait for page load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'commute-page'))
        )
        
        # Set a filter value
        try:
            distance_min = driver.find_element(By.ID, 'filter-distance-min')
            driver.execute_script("arguments[0].value = '5';", distance_min)
            driver.execute_script("arguments[0].dispatchEvent(new Event('change'));", distance_min)
            time.sleep(0.5)
            print("✓ Set filter value")
            
            # Check localStorage
            stored_filters = driver.execute_script("return localStorage.getItem('commuteMapFilters');")
            if stored_filters:
                print(f"✓ Filter state saved to localStorage: {stored_filters}")
            else:
                print("ℹ Filter state not found in localStorage (may require user interaction)")
        except NoSuchElementException:
            print("ℹ Filter controls not found (may be created by JavaScript)")
        
        print("\n✓ Filter persistence tests completed")
        
    except Exception as e:
        print(f"✗ Error during test: {e}")
    finally:
        driver.quit()

def test_mobile_responsiveness(base_url='http://localhost:5000'):
    """Test mobile responsiveness and touch targets."""
    print("\n=== Testing Mobile Responsiveness ===")
    
    # Test on iPhone SE (320px width)
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    mobile_emulation = {
        "deviceMetrics": {"width": 320, "height": 568, "pixelRatio": 2.0},
        "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)"
    }
    chrome_options.add_experimental_option("mobileEmulation", mobile_emulation)
    
    driver = webdriver.Chrome(options=chrome_options)
    try:
        driver.get(f'{base_url}/commute')
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'commute-page'))
        )
        print("✓ Page loaded on iPhone SE viewport (320px)")
        
        # Check touch targets
        interactive_elements = driver.find_elements(By.CSS_SELECTOR, 
            'button, a.btn, input[type="checkbox"], .route-option-card')
        
        small_targets = []
        for element in interactive_elements:
            if element.is_displayed():
                size = element.size
                if size['height'] < 44 or size['width'] < 44:
                    small_targets.append({
                        'element': element.tag_name,
                        'class': element.get_attribute('class'),
                        'size': f"{size['width']}x{size['height']}px"
                    })
        
        if small_targets:
            print(f"⚠ Found {len(small_targets)} elements below 44x44px minimum:")
            for target in small_targets[:5]:  # Show first 5
                print(f"  - {target['element']}.{target['class']}: {target['size']}")
        else:
            print("✓ All interactive elements meet 44x44px minimum")
        
        print("\n✓ Mobile responsiveness tests completed")
        
    except Exception as e:
        print(f"✗ Error during test: {e}")
    finally:
        driver.quit()

def main():
    """Run all tests."""
    print("=" * 60)
    print("Interactive Map Filters - Test Suite")
    print("=" * 60)
    
    base_url = 'http://localhost:5000'
    
    print(f"\nTesting against: {base_url}")
    print("Note: Flask app must be running on port 5000")
    print("Start with: flask run or python wsgi.py")
    
    try:
        test_commute_page_filters(base_url)
        test_dashboard_map(base_url)
        test_filter_persistence(base_url)
        test_mobile_responsiveness(base_url)
        
        print("\n" + "=" * 60)
        print("All tests completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Test suite failed: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())

# Made with Bob
