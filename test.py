import time
# time.sleep(999999)
import re
from datetime import datetime
from dateutil.relativedelta import relativedelta
from tqdm import tqdm
import os
import glob
import smtplib, ssl
import email.message
from shutil import rmtree
from shutil import move
from tabulate import tabulate
from PIL import Image, ExifTags
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

# ============================== INI VARIABLES ==================================
##AdminPhoto
url_login = "https://myblog.com/acceder"					#LoginURL
url_create = "https://myblog.com/wp-admin/post-new.php?post_type=sunshine-gallery"
user = "info@myblog.com"
passw = "Password$"

##Mail
port = 587  # For SSL
smtp_server = "smtp.zoho.eu"
sender_email = "robot@myblog.com"  # Enter your address
password = "Password$"

##Path
production_mode = True
if production_mode:
    receiver_email = ["info@hotmail.com", "info@myblog.com"]
    # receiver_email = ["alberto11651@hotmail.com"]
  
    path = "/RobotWeb/en_cola"
    errors = "/RobotWeb/con_errores"
    processed = "/RobotWeb/procesados"
    water_mark = "/RobotWeb/watemark.png"

    chrome_options = Options()
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')

    
else:
    receiver_email = ["info@hotmail.com"]
    
    cwd = os.getcwd()
    path = os.path.join(os.getcwd(), r"en_cola")
    errors = os.path.join(os.getcwd(), r"con_errores")
    processed = os.path.join(os.getcwd(), r"procesados")
    water_mark = os.path.join(os.getcwd(),  "watemark.png")
    
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    

##Variables
error_notification = []
sucess_notification = []
dic_exif = {1: 0, 8: 90, 3: 180, 6: -90}

python_watemark = True
allow_comments = True
block_after_seleccion = True
add_watemark = False
send_customer_email = True
extra_image = False

# ============================== FUNCTIONS ==================================
def login(user, passw):
    time.sleep(10)
    driver.find_element_by_id("user_login").send_keys(user)
    password = driver.find_element_by_id("user_pass")		
    password.send_keys(passw)
    password.send_keys(Keys.ENTER)
    driver.get(url_create)
    return


def scanfolders(path):
    folders = []
    for root, dirs, files in os.walk(path, topdown=False):
       for folder in dirs:
          if folder != "@eaDir":
              folders.append(folder)


    return folders

def files_in_folder(path, folder):
    extensions = ("*JPG","*.jpg","*.jpeg",)
    list = []
    for extension in extensions:
        list.extend(glob.glob(os.path.join(path, folder) + "/" + extension))
    return list        
        
def stripe_folder_data(folder):
    try:
        split = folder.split('. ', 1)
        if len(split) == 1: 
            mail = ""
            name_gallery = folder
        elif len(split) == 2:
            mail = split[0]
            name_gallery = split[1]
        else:
            mail = ""
            name_gallery = folder

    except:
        mail = ""
        name_gallery = folder
        
    return mail, name_gallery

def moverFolderFinished(destination):
    ## If already move, delete and move new.
    if os.path.isdir(os.path.join(destination, folder)):
        rmtree(os.path.join(destination, folder), ignore_errors=True)
    move(os.path.join(path, folder), destination)

    return


def sanitycheck():
    sanity_check_pass = True
    ##Move folders with empty email to error folder
    if mail == "":
        ## If already move, delete and move new.
        moverFolderFinished(errors)
        error_notification.append([folder, "NO subido - Falta contrasena"])
        sanity_check_pass = False

    ##Move empty folders to error folder
    elif len(images) == 0:
        ## If already move, delete and move new.
        moverFolderFinished(errors)
        error_notification.append([folder, "NO subido - Carpeta sin imagenes"])
        sanity_check_pass = False

    return sanity_check_pass

##Function
def resize_rotate_watemark():
    error_image_preprocessing = False

    if python_watemark:
        for image_path in images:
            print("resizing: ", image_path)

            ##Load image
            main = Image.open(image_path)
            mark = Image.open(water_mark)
            
            ##Try rotate
            try: ##Read orientation tag
                exif = {ExifTags.TAGS[k]: v for k, v in main._getexif().items() if k in ExifTags.TAGS}
            except: ##If there is no orientation tag available
                exif = {'Orientation': 1}
                error_image_preprocessing = True
    
            ##Orientation to degree:
            try: ##If conversion orientation-degree exists
                degree = dic_exif[exif['Orientation']]
                main = main.rotate(degree, expand=1)
    
            except: ## If doesnt exists, dont rotate.
                error_image_preprocessing = True
                
            ##Watemark and scale
            try:    
                mark_width, mark_height = mark.size
                main_width, main_height = main.size
                aspect_ratio = mark_width / mark_height
                new_mark_width = main_width * 0.25
                mark.thumbnail((new_mark_width, new_mark_width / aspect_ratio), Image.ANTIALIAS)
            
                tmp_img = Image.new('RGB', main.size)
            
                for i in range(0, tmp_img.size[0], mark.size[0]):
                    for j in range(0, tmp_img.size[1], mark.size[1]):
                        main.paste(mark, (i, j), mark)
                        main.thumbnail((8000, 8000), Image.ANTIALIAS)
                        # main.save(final_image_path, quality=100)
                        
                main.thumbnail((900, 900))
                main.save(image_path, quality=75)
                
            except:
                error_image_preprocessing = True
                
    if error_image_preprocessing:
        error_notification.append([folder, "Error: marca de agua y rotacion"])
            
    return


def create_gallery():  
    driver.get(url_create)

    time.sleep(2)
    driver.find_element_by_name("post_title").send_keys(name_gallery)
    time.sleep(1)
    
    ###Select protect by password
    select = Select(driver.find_element_by_name('sunshine_gallery_status'))
    select.select_by_visible_text("Protegido por contraseña")
    time.sleep(1)

    ###Password
    sunshine_gallery_password = driver.find_element_by_name("sunshine_gallery_password")
    sunshine_gallery_password.send_keys(mail)   
    time.sleep(1)
    
    # ##expiration date
    # driver.find_element_by_name("expired_at").send_keys((datetime.today() + relativedelta(months=1)).strftime("%d/%m/20%y"))


def upload():
    time.sleep(2)
    
    ##Add images
    for image in images:
    # for image in tqdm(images):
        print("upload: ", image)
        driver.find_element_by_xpath("//input[@type='file']").send_keys(image)
        time.sleep(3)
    time.sleep(10)
    
    print("todas imagenes arrastradas")

    ## Wait until loader dissapear.
    while False:
        try:
            WebDriverWait(driver, 1).until(EC.presence_of_element_located((By.XPATH, "//div[@class='success']")))
        except:
            break
    time.sleep(3)
    
    print("Marcador subido con exito encontado. Continuar.")
    
    ##Go to the top
    driver.find_element_by_tag_name('body').send_keys(Keys.CONTROL + Keys.HOME)
    time.sleep(2)
    
    ##Save
    publish = driver.find_element_by_xpath("//div[@id='publishing-action']//input[@id='publish']")
    publish.click()
    time.sleep(1)


  
def notifications():
    msg = email.message.Message()
    msg.add_header('Content-Type','text/html')
    
    ##If there is some error
    if len(error_notification) > 0:
        body = [['/!\ Errores --------', '--- MOTIVO ---']] + error_notification + [['OK procesados', '=======']] + sucess_notification
        body = tabulate(body, tablefmt='html')
        msg['Subject'] = '/!\ Error Robot - Galerias myblog.com'
        
    #If everything is OK.
    else:
        body = [['|OK| procesados =======', '==========']] + sucess_notification
        body = tabulate(body, tablefmt='html')
        msg['Subject'] = 'OK Robot - Galerias myblog.com'

    msg.set_payload(body)
    send_email(msg)
        
    return


def send_email(msg):
    msg['From'] = sender_email
    try:
        with smtplib.SMTP(smtp_server, port) as server:
            context = ssl.create_default_context()
            server.starttls(context=context)
            server.login(sender_email, password)
            msg['To'] = ", ".join(receiver_email)                
            server.sendmail(msg['From'], receiver_email, msg.as_string())
            server.quit()

                
    except Exception as e:
        print("No se puede conectar con el servicio de email.", e)
        
    return
# ============================== LOGIC ==================================
folders = scanfolders(path)

try:
    ##If there is some work to be done
    if len(folders) > 0:
        # ###load webdriver
        driver = webdriver.Chrome(chrome_options=chrome_options)
        # driver = webdriver.Chrome()
        driver.get(url_login)
        
        ##Login
        login(user, passw)
        
        ##New gallery
        pbar = tqdm(folders)
        for folder in pbar:
            pbar.set_description("%s" % folder)
            ##List images
            images = files_in_folder(path, folder)
            ##Extract data from folder
            mail, name_gallery = stripe_folder_data(folder)
            ##Sanity check before start
            sanity_check_pass = sanitycheck()
            
            
            if sanity_check_pass:
                try:
                    resize_rotate_watemark()
                    create_gallery()
                    upload()
                    # notify_customer()
                    moverFolderFinished(processed)
                    sucess_notification.append([folder, "OK - subido"])
    
                except Exception as e:
                    error_notification.append([folder, "No publicado: " + str(e)])
                
        
        notifications()
        
        print(error_notification + sucess_notification)
    
except Exception as e:
    error_notification.append(["Error general", "Necesita revision de Alberto; " + str(e)])
    notifications()