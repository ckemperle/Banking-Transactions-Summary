#%%-------------------------------------------------------------
def setpath():
    try:
        with open(f'data/env_variables.pickle', 'rb') as handle:
                environment = pickle.load(handle)

    except Exception as err:
        if isinstance(err,FileNotFoundError):

            environment=dict()
            environment['Raika_path'] = input('Path to folder:')
            environment['download_folder'] = input('Path to Download folder:')
            environment['Raika_login_usr'] = input('Verfügernummer:')
            environment['Raika_login_pw'] = input('Passwort:')
            environment['Raika_discord'] = input('Discord Key:')

            with open(f'data/env_variables.pickle', 'wb') as handle:
                    pickle.dump(environment, handle)
        else:
            sys.exit(err)

    os.environ['Raika_path'] = environment.get('Raika_path')
    os.environ['download_folder'] = environment.get('download_folder')
    os.environ['Raika_login_usr'] = environment.get('Raika_login_usr')
    os.environ['Raika_login_pw'] = environment.get('Raika_login_pw')
    os.environ['Raika_discord'] = environment.get('Raika_discord')

#%%-------------------------------------------------------------
def webScraping():
    print("Starting Webscraping...")

    #set Chrome Driver and navigate to login website
    os.chdir(os.environ.get('Raika_path'))
    #driver = webdriver.Chrome(f'{os.environ.get("Raika_path")}/chromedriver')
    driver = webdriver.Chrome(f'{os.environ.get("Raika_path")}/chromedriver.exe') #for windows
    driver.get("https://sso.raiffeisen.at/login/#/identifier/signInChooser")
    driver.maximize_window() #full screen

    #login
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '/html/body/div/main/login/section/div/div/div/div/div/login-verfueger-login/div[1]/form/fieldset/div/div[2]/div[1]/div/div/div[1]'))).click() #search list for styria
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '/html/body/div/main/login/section/div/div/div/div/div/login-verfueger-login/div[1]/form/fieldset/div/div[2]/div[1]/div/div/div[1]/ul/li/div[8]/span/span'))).click() #search styria
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '/html/body/div/main/login/section/div/div/div/div/div/login-verfueger-login/div[1]/form/fieldset/div/div[2]/div[2]/div/div/input'))).send_keys(os.environ.get('Raika_login_usr'), Keys.RETURN) #paste verfügernummer

    print("Wait for login...", end="")
    WebDriverWait(driver, 1000).until(EC.element_to_be_clickable((By.XPATH, '/html/body/div/main/login/section/div/div/div/div/div/login-pin-input/div/form/fieldset/div[2]/div/input'))).send_keys(os.environ.get('Raika_login_pw'), Keys.RETURN) #paste password and wait for confirmation

    time.sleep(5)
    text = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, '/html/body/div/main/login/section/div/div/div/div/div/login-pushtan/div/div[2]/p'))).text #save log-in text for discord

    #send message via discord
    cmd = f'python discord_bot.py {text}'
    subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    del text

    WebDriverWait(driver, 1000).until(EC.element_to_be_clickable((By.XPATH, '/html/body/div/main/drb-multi-dashboard/div/drb-multi-view-dashboard/div/div[2]/div/div/div/drb-multi-view-dashboard-page/ul/li[2]/drb-multi-view-widget/section/div/div[2]/ums-umsatz-widget/drb-widget-header-large/header/a/div/div/div/h3'))).click() #navigate to download
    print("Success!")

    WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, '/html/body/div[1]/main/drb-page/div/div/div/ktz-kontozentrale-page/ng-switch/div/drb-page-body/section/div/div/article/div[2]/drb-page-fragment/div/div/div/ums-umsatz-page-fragment/ums-page-konto/div/div/div[2]/div[2]/a'))).click() #start csv download
    time.sleep(5) #wait for download to start

    #logout
    WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.XPATH, '/html/body/div[1]/header/nav/drb-meta-nav/ng-transclude/pfp-logout-button/button/span[2]'))).click() #click logout button
    time.sleep(5)
    driver.quit() #quit webdriver
    print("Finished Webscraping!")

#%%-------------------------------------------------------------
def dataCleaning():
    print("Data cleaning has started...", end="")
    try:
        filename = [name.name for name in os.scandir(os.chdir(os.environ.get('download_folder'))) if 'meinelba' in name.name][0] #search new raika file
    except:
        sys.exit('No file to clean...')
    file = pd.read_csv(f'{os.environ.get("download_folder")}/{filename}', sep = ';', header=None, usecols = [1,2,3]) #read csv
    file.columns = ['Auftrag', 'Datum', 'Betrag'] #3 columns
    file.Datum = pd.to_datetime(file.Datum, format='%d.%m.%Y') #convert date to datetime
    file.Betrag = [betrag.replace(',', '.') for betrag in file.Betrag] #german , replacement to english .
    file['Betrag'] = file['Betrag'].astype(float) #convert to float number
    exp = pd.DataFrame(
            [[auftrag.partition(' ')[0], auftrag.partition(' ')[2],  betrag] for auftrag, betrag in zip(file['Auftrag'], file['Betrag']) if betrag < 0]
            ) #search for expenses

    for auftrag1, auftrag2, betrag in zip(enumerate(exp[0]), exp[1], exp[2]): #simple sentiment to get Verwendungszweck and Zahlungsempfänger
        if ('Zahlungsempfänger' in auftrag1[1]) or ('Verwendungszweck' in auftrag1[1]) or ('Zahlungsreferenz' in auftrag1[1]):
            exp.iloc[auftrag1[0], 0] = auftrag2.partition(' ')[0]
    exp = exp.iloc[:, [0,2]]
    exp.columns = ['Firma', 'Summe']
    exp = exp.groupby(by='Firma').sum().reset_index() #sum up expenses by Zahlungsempfänger
    exp.replace('DIE', 'BAUSATZ', inplace=True) #replace words
    exp.replace('ONLINE', 'Sonstiges', inplace=True) #replace online
    income, outcome = [[income for income in file['Betrag'] if income > 0], [outcome for outcome in file['Betrag'] if outcome < 0]] #merge expenses together with rest
    file = file.groupby(by='Datum').sum() #sum up by date to get daily values
    file.reset_index(inplace=True) #reset index

    if os.path.exists(f'{filename}'): #delete raika file
        os.remove(f'{filename}')
        print('Deleted File successfully!')
    else:
        print('File does not exist')

    date = file.copy()
    company = exp.copy()

    os.chdir(os.environ.get('Raika_path'))
    currentYear = datetime.now().year #get current year

    #get loaded file
    try:
        #load file
        with open(f'data/date_{currentYear}.pickle', 'rb') as handle:
            dateLoad = pickle.load(handle)
        with open(f'data/company_{currentYear}.pickle', 'rb') as handle:
            companyLoad = pickle.load(handle)

        date = date.append(dateLoad).reset_index(drop=True) #merge old values with new values
        company = company.append(companyLoad).groupby('Firma').sum().reset_index() #merge old values with new values
    #no file is saved
    except:
        pass

    #save file
    with open(f'data/date_{currentYear}.pickle', 'wb') as handle:
        pickle.dump(date, handle)
    with open(f'data/company_{currentYear}.pickle', 'wb') as handle:
        pickle.dump(company, handle)

    print("Success!")

#%%-------------------------------------------------------------
def plot(type, year): #simple plotly plot
    os.chdir(os.environ.get('Raika_path'))
    if type=='companies':
        with open(f'data/company_{year}.pickle', 'rb') as handle:
            df = pickle.load(handle)
        df = df.sort_values(by='Summe')
        fig = px.bar(x=df['Firma'], y=df['Summe']*-1, title=f'Firmenausgaben', labels={'x': 'Firma', 'y': 'Summe'})
        fig.show()

    else:
        with open(f'data/date_{year}.pickle', 'rb') as handle:
            df = pickle.load(handle)
        df['Datum'] = pd.to_datetime(df['Datum'])
        df = df.sort_values(by='Datum')

        fig = px.line(x=df['Datum'], y=df['Betrag'], title=f'Zeitreihe Ausgaben', labels={'x': 'Datum', 'y': 'Betrag'})
        fig.update_layout(autosize=False,
                                      width=900,
                                      height=600)
        fig.show()

def printDf(year):
    os.chdir(os.environ.get('Raika_path'))
    with open(f'data/date_{year}.pickle', 'rb') as handle:
            df = pickle.load(handle)
    df['Datum'] = pd.to_datetime(df['Datum'])
    df = df.sort_values(by='Datum')
    print(df)

    with open(f'data/date_{year}.pickle', 'rb') as handle:
            df = pickle.load(handle)
    print(df)
#%%-------------------------------------------------------------
if __name__ == "__main__":
    import os
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import Select
    from selenium.webdriver.common.keys import Keys
    import time
    import pandas as pd
    import matplotlib.pyplot as plt
    from datetime import datetime
    import openpyxl
    import pickle
    import plotly.express as px
    from datetime import datetime
    import subprocess

    setpath()

    loop = True
    while loop:

        print('\n Numbers for actions: \n ------------- \n 1: Scrap current month \n 2: clean downloaded data \n 3: Plot Companies \n 4: Plot date \n 5: Print Dataframe \n 6: exit \n ------------- \n')

        action = int(input('Number: '))

        if action == 1:
            try:
                webScraping()
                dataCleaning()
            except BaseException as e:
                print(e)
                print('Some Error accured...')

        elif action == 2:
            try:
                dataCleaning()
            except BaseException as e:
                print(e)
                print('Some Error accured...')

        elif action == 3:
            try:
                year = int(input('Plot Year '))
            except:
                year=datetime.now().year
            plot('companies', year)

        elif action == 4:
            try:
                year = int(input('Plot Year '))
            except:
                year=datetime.now().year
            plot('date', year)

        elif action == 5:
            try:
                year = int(input('Plot Year '))
            except:
                year=datetime.now().year
            printDf(year)

        elif action == 6:
            time.sleep(2)
            loop = False