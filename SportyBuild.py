#This is outdated. I will add the prper one later

import time
from datetime import date

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

time_stamp = date.today()

chrome_options = Options()
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--headless')

MAXIMUM_ODD = 1.2
MAXIMUM_GAME = 5
STAKE_AMOUNT = 100


def clear_box(web_element):
    web_element.send_keys(Keys.CONTROL + "a")
    web_element.send_keys(Keys.BACKSPACE)


def check_simulated(name):
    if 'simulated' in name.lower():
        return True
    else:
        return False


def sporty_bet():
    global time_stamp
    driver = webdriver.Chrome(executable_path = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                              options = chrome_options)
    driver.get("https://www.sportybet.com/gh/sport/football/today")

    driver.implicitly_wait(5)

    username = driver.find_element(By.XPATH, "//input[@name='phone' and @placeholder='Mobile Number']")
    clear_box(username)
    username.send_keys("YOUR_USERNAME")
    time.sleep(2)

    password = driver.find_element(By.XPATH, "//input[@type='password' or @placeholder='Password']")
    clear_box(password)
    password.send_keys("YOUR_PASSWORD")
    time.sleep(2)

    login_btn = driver.find_element(By.XPATH, "//button[@name='logIn' and .='Login']")
    login_btn.click()
    time.sleep(5)

    try:
        driver.find_element(
            By.XPATH,
            "//div[@class='m-winning-wrapper']//i[@class='m-icon-close']").click()
    except NoSuchElementException:
        pass

    # GET THE NUMBER OF LEAGUE AVAILABLE
    # Function to check if 3 or more outcomes are below a certain odd threshold
def check_outcomes(predictions, threshold):
    count = 0
    for prediction in predictions:
        if float(prediction.text) < threshold:
            count += 1
    return count >= 3

# Function to evaluate and select outcome based on specified conditions
def evaluate_and_select_outcome(team_stats):
    # Example logic:
    # Select outcome based on which team has better form, higher league position, fewer injuries, etc.
    # Replace with your specific logic
    
    # Example: Selecting the outcome for the team with better form
    if team_stats['team_A']['form'] > team_stats['team_B']['form']:
        return 'team_A'
    else:
        return 'team_B'

# Main loop to iterate through leagues and matches
for lg_post in range(1, f_leagues + 1):
    league_name = driver.find_element(
        By.XPATH,
        f"(//div[@class='match-league'])[{lg_post}]/div[@class='league-title']/span[@class='text']"
    ).text
    
    if not check_simulated(league_name):
        driver.find_element(By.XPATH, f"(//div[.= 'Double Chance'])[{lg_post}]").click()
        match_per_league = len(driver.find_elements(By.XPATH,
                                                    f"(//div[@class='match-league'])[{lg_post}]//div[contains(@class,'match-row')]"))

        for m_post in range(1, match_per_league + 1):
            try:
                match_Hdc = driver.find_element(
                    By.XPATH,
                    f"(//div[@class='match-league'])[{lg_post}]//div[contains(@class, 'match-row')][{m_post}]//div[@class='m-outcome'][1]"
                )
                match_Hdc_oc = float(match_Hdc.text)
                
                # Click on the match to open it
                match_Hdc.click()
                
                # Scraping predictions for this match
                predictions = driver.find_elements(By.XPATH, "//div[@class='prediction']")
                
                # Checking if 3 or more predictions are below MAXIMUM_ODD
                if check_outcomes(predictions, MAXIMUM_ODD):
                    # Evaluate and select outcome based on team stats
                    team_stats = {
                        'team_A': {
                            'form': 8,  # Example: Replace with actual form rating
                            'league_position': 2,  # Example: Replace with actual league position
                            'injured_players': 1,  # Example: Replace with actual count of injured players
                            'lineup_quality': 'good'  # Example: Replace with actual lineup quality evaluation
                        },
                        'team_B': {
                            'form': 7,
                            'league_position': 4,
                            'injured_players': 3,
                            'lineup_quality': 'average'
                        }
                    }
                    
                    selected_team = evaluate_and_select_outcome(team_stats)
                    
                    # Click on the corresponding prediction
                    driver.find_element(By.XPATH, f"//div[@class='prediction'][{selected_team}]").click()
                    match_clicked += 1
                
                # Close the match details if needed (not clear from original code)
                # driver.find_element(By.XPATH, "//button[@class='close-button']").click()
                
            except NoSuchElementException:
                pass
            
            # Break if maximum games limit is reached
            if match_clicked > MAXIMUM_GAME:
                break
        
        # Break if maximum games limit is reached
        if match_clicked > MAXIMUM_GAME:
            break

    # ENTER BET AMOUNT
    betslip = driver.find_element(By.CSS_SELECTOR, "input[placeholder='min. 10']")
    clear_box(betslip)
    time.sleep(5)
    betslip.send_keys(STAKE_AMOUNT)

    actions = ActionChains(driver)
    wait = WebDriverWait(driver, 30)

    # PLACE BET
    place_bet = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.af-button")))
    time.sleep(5)
    actions.double_click(place_bet).perform()

    try:
        time.sleep(2)
        driver.find_element(By.XPATH, "//span[text()='Accept Changes']")
    except NoSuchElementException:
        pass

    confirm_bet = wait.until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.af-button.af-button--primary:nth-child(2)")))
    confirm_bet.click()

    time.sleep(5)

    with open('logfile.txt', 'a') as file:
        file.write(f"{match_clicked} matches clicked on {time_stamp} staked successfully.")
        file.write("\n")

    driver.close()
    driver.quit()


sporty_bet()
