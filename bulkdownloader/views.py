# Python script : Wikimedia Commons Bulk Downloader By Category
import requests
import aiohttp
import asyncio
import aiofiles
from bs4 import BeautifulSoup
import urllib
import json
import os
import time
from django.shortcuts import render, redirect
from bulkdownloader import config
from flask import request
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import csv
import configparser
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from django.contrib.auth import login, authenticate, logout #add this
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm #add this
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .models import history
from datetime import datetime





#config = configparser.ConfigParser()
# Read Configurations
# config.read('wiki-config.ini')
# print(config)

url = config.url
response_url = url+"/wiki/"
URL = url
data_file = config.csv_file


ses = requests.Session()
ses.verify = False

max_records = -1
limit = 500

# Commons API URL
wc_url = "https://commons.wikimedia.org/w/api.php"

# Print empty line
def print_line():
	print("-"*80)

s_time = time.time()
	
print_line()


# Limit value should be less than or equal to 500
if (limit > 500):
	limit = 500

# Validate the max_records and limit value
if (max_records != -1 and max_records < limit):
	limit = max_records

# Getting next offset value from json response
def get_next_offset(res):
	if ("continue" in res and "cmcontinue" in res["continue"]):
		return res["continue"]["cmcontinue"]
	return None

@login_required(login_url='/login/')
def home(request):
    wiki_acct_msg = ""
    
    if 'wiki_acct_msg' in request.session:
        wiki_acct_msg = request.session['wiki_acct_msg']
        request.session['wiki_acct_msg'] = wiki_acct_msg
    if 'username' in request.session:
        username = request.session['username']
    
    else:
        request.session['wiki_acct_msg'] = ''
        username = ''
    print(username)
    if request.method == 'POST':
        
        if 'wiki-account' in request.POST:
            username = request.session['username']
            password = request.session['password']

            CSRF_TOKEN = wiki_login(username,password)
            request.session['CSRF_TOKEN'] = CSRF_TOKEN
            wiki_acct_msg = 'Connected successfully!'
            request.session['wiki_acct_msg'] = wiki_acct_msg
            messages.success(request, 'Connected successfully!', extra_tags='alert')
    if 'wiki_acct_msg' in request.session and request.session['wiki_acct_msg'] != '':
        wiki_acct_msg = request.session['wiki_acct_msg']
        request.session['wiki_acct_msg'] = wiki_acct_msg
    else:
        wiki_acct_msg = 'not connected'
        request.session['wiki_acct_msg'] = wiki_acct_msg

    print(request.session['wiki_acct_msg'])
    return render(request, 'home.html',{'username_val':username,'wiki_acct_msg':request.session['wiki_acct_msg']})

# Fetching all file names in particular category

def fetch_all_file_names_in_category(next_offset, category):
    category = config.category + str(category)
    file_names = []
    ses = requests.Session()
    ses.verify = False
    while next_offset != None and (len(file_names) < max_records or max_records == -1):
        #req = ses.get(url=settings.wc_url, params=params_data)
        params_data = {
        "action": "query",
        "format": "json",
        "list": "categorymembers",
        "cmtitle": category,
        "cmlimit": limit,
        "cmsort": "timestamp",
        "cmdir": "desc"
        }
        req = requests.get(wc_url,params = params_data,verify=False)
        d = req.json()
        next_offset = get_next_offset(d)
        itemlist = d["query"]["categorymembers"]

        for item in itemlist:
            file_names.append(item["title"])

        if (next_offset != None):
            bal_count = max_records - len(file_names)
        if (max_records != -1 and bal_count < limit):
            params_data["cmlimit"] = bal_count
        if (next_offset != None):
            params_data["cmcontinue"] = next_offset
        fetch_all_file_names_in_category(next_offset, category)
    
    return file_names,len(file_names)


#print_line()
#print("Fetching file names....")
#print("Total files count: " + str(len(final_files_list)))
#print("Total time for Fetching file names: %.2f secs" % (time.time() - s_time))

# Getting download url from commons html page

async def get_file_download_link(session, file_name):
	url = "https://commons.wikimedia.org/wiki/"+file_name
	try:		
		async with session.get(url,ssl=False) as response:
			html_body = await response.read()
			soup = BeautifulSoup(html_body, "html.parser")
			media = soup.findAll("div", attrs={"class":"fullMedia"})
			dl = media[0].find('a').get("href")
			f_dl = urllib.parse.unquote(dl)
			# print(file_name + " => " + f_dl)
			return f_dl

	except BaseException as e:
		print_line()
		print("An exception occurred " + file_name)
		print(e)
		

# Download file from commons download link

async def save_downloaded_file(session, dl, index, total_links_count,category=""):
    try:
        async with session.get(dl, allow_redirects=True,ssl=False) as audio_request:
            if audio_request.status == 200:
                d_filename = urllib.parse.unquote(dl).split("/")[-1]
                # print(str(index+1) + "/" + str(total_links_count) + " => " + d_filename)
                dest_folder = category.replace(" ", "_")
                file_path = os.path.join(dest_folder, d_filename)
                f = await aiofiles.open(file_path, mode='wb')
                await f.write(await audio_request.read())
                await f.close()

    except BaseException as e:
        print_line()
        print("An exception occurred while downloading " + dl)
        print(e)


# Task to Start getting download links then download files from download links
download_links = []

async def fetch_download_links_and_download_file(final_files_list,category):
    print_line()
    async with aiohttp.ClientSession() as session:
        tasks = []
        print("Fetching download links....")
        new_final_files_list = []
        for index, f in enumerate(final_files_list):
            task = asyncio.ensure_future(get_file_download_link(session, f))
            tasks.append(task)
			
        temp_download_links = await asyncio.gather(*tasks)
        download_links = list(filter(None, temp_download_links)) # Filter valid links
        print("Total time for Scraping download links: %.2f secs" % (time.time() - s_time))
        total_links_count = len(download_links)
        print("Total download links: " + str(total_links_count))
		
		
		# Start Download Task
		# Download file from commons download link 
		
		# create folder if it does not exist
        dest_folder = category.replace(" ", "_")
        if not os.path.exists(dest_folder):
            os.makedirs(dest_folder)
		
        print_line()
        print("Please wait %s files are Downloading...." % (str(total_links_count))) 
        download_tasks = []
        for index, dl in enumerate(download_links):
            print(download_links,"jhfbjbhbbhbfh")
            download_task = asyncio.ensure_future(save_downloaded_file(session, dl, index, total_links_count,category))
            download_tasks.append(download_task)
        download_files = await asyncio.gather(*download_tasks)
        print("Total time for Download files : %.2f secs" % (time.time() - s_time))
        print("Total downloaded files: " + str(len(download_files)))
        print_line()

        print("All files are downloaded under: " + dest_folder)
        print_line()


def wiki_login(username, password):
    ses = requests.Session()
    ses.verify = False
    # Retrieve login token first
    
    PARAMS_0 = {
        'action':"query",
        'meta':"tokens",
        'type':"login",
        'format':"json"
    } 
    #print(ses)
    R = ses.get(url=URL, params=PARAMS_0, verify=False)
    DATA = R.json()
    print(DATA,"Login token data")
    LOGIN_TOKEN = DATA['query']['tokens']['logintoken']
    PARAMS_1 = {
        'action':"clientlogin",
        'lgname': username,
        'lgpassword': password,
        'lgtoken':LOGIN_TOKEN,
        'format':"json"
    }
    R = ses.post(URL, data=PARAMS_1, verify=False)

    PARAMS_2 = {
        'action':"query",
        'meta':"tokens",
        'type':"csrf",
        'format':"json"
    }
    R = ses.get(url=URL, params=PARAMS_2, verify=False)
    DATA = R.json()
    print(DATA,"CSRF token data")
    CSRF_TOKEN = DATA['query']['tokens']['csrftoken']
    #upload_data_into_wiki(CSRF_TOKEN)
    return CSRF_TOKEN

  
def upload_data_into_wiki(CSRF_TOKEN, row):
    PARAMS_3 = {
        "action": "edit",
        "format": "json",
        "title": row[0],
        "text": row[1],
        "summary": "Upload the word %s" % row[0],
        "token": CSRF_TOKEN
    }
    R = ses.post(url=URL, data=PARAMS_3, verify=False)
    print(R.url)
    print(R.json)

def user_login(request):
    error_msg = ""
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request,user)
                request.session['username'] = username
                request.session['password'] = password
                messages.info(request, f"You are now logged in as {username}.")
                return redirect("/home/", username_val=username)
                
            else:
                error_msg = "username or password."
                messages.error(request,"Invalid username or password.")
                
        else:
            error_msg = "username or password."
            messages.error(request,"Invalid username or password.")
    form = AuthenticationForm()
    
    return render(request, 'login.html', {"login_form":form,"error_msg":error_msg})
    #render(request, 'home.html', {'d': d,'count': count, 'search': category,'final_list':final_files_list})
    
@login_required(login_url='/login/')
def user_logout(request):
	#logout(request)

    logout(request)
    if 'username' in request.session:
        del request.session['username']
    if 'password' in request.session:
        del request.session['password']
    if 'wiki_acct_msg' in request.session:
        del request.session['wiki_acct_msg']
    messages.info(request, "You have successfully logged out.")
    return redirect("/login/")




@login_required(login_url='/login/')
def media_download(request):
    if request.method == 'POST':
        page = request.GET.get('page', 1)
        if 'search' in request.POST or request.POST.get('search_value'):
            page = request.GET.get('page', 1)
            category = request.POST.get('search_value')
        if 'download' in request.POST:
            category = request.POST.get('search_value')
            page = request.GET.get('page', 1)
            flag = 1
            final_files_list = request.POST.getlist('final_list[]')
            if request.POST.getlist('file_name[]'):
                final_files_list = request.POST.getlist('file_name[]')
            else:
                final_files_list=final_files_list
            asyncio.run(fetch_download_links_and_download_file(final_files_list,category))
            messages.success(request, 'Files downloaded successfully!', extra_tags='alert')
    else:
        category = "CHECK"
    

	# Setting base params
    next_offset = ""

    #ses = requests.Session()
    d,count=fetch_all_file_names_in_category(next_offset, category)


    filtered_list = []
    for file_name in d:
        if (file_name.startswith("File:")):
            filtered_list.append(file_name)

    final_files_list = list(set(filtered_list))
    
    
    page = request.GET.get('page', 1)
    paginator = Paginator(d, 10)
    try:
        d = paginator.page(page)
    except PageNotAnInteger:
        d = paginator.page(1)
    except EmptyPage:
        d = paginator.page(paginator.num_pages)
    params_data = {
            "action": "query",
            "format": "json",
            "list": "categorymembers",
            "cmtitle": "Category:Files uploaded by spell4wiki",
            "cmlimit": 500,
            "cmsort": "timestamp",
            
            }
    R = requests.get(wc_url,params = params_data,verify = False)
    #R = S.get(url=URL, params=PARAMS)
    DATA = R.json()
    PAGES = DATA["query"]["categorymembers"]
    cat_list=[]
    for i in PAGES:
        if  not (i['title'].startswith("File:")):
            c=i['title'].split()
            cat_list.append(c[-1])
    username_val  = request.session['username']
    return render(request, 'media_download.html', {'d': d,'count': count, 'search': category,'final_list':final_files_list,'categories':cat_list,'username_val':username_val})

@login_required(login_url='/login/')
def wiki_dict_upload(request):
    history_val_dict = {}
    username_val  = request.session['username']
    if request.method == 'POST':
        if 'dict_upload' in request.POST or request.POST.get('dict_file'):
            file_name = request.POST.get('dict_file')
            username = request.session['username']
            password = request.session['password']
            CSRF_TOKEN = request.session['CSRF_TOKEN']
            ses = requests.Session()
            ses.verify = False
            #Trigger point
            with open(file_name,'r') as csvfile:
                csvreader=csv.reader(csvfile)
                fields=next(csvreader)
                for row in csvreader:
                    R = ses.get(url=response_url)
                    if R.status_code != "":
                        print(CSRF_TOKEN, row)
                        msg_val = "%s word added into wikitionary" % row[0]
                        print ("%s word added into wikitionary" % row[0])
                        upload_data_into_wiki(CSRF_TOKEN, row)
                        print(datetime.utcnow())
                        history_val = history(command = str(msg_val),file_name = str(file_name),type ="Add" ,tool_type ="wikitionary" ,created_on = datetime.utcnow() ,created_by =username)
                        history_val.save()
                        history_val_dict ={
                             'command':str(msg_val),
                             'file_name': str(file_name),
                             'type': "Add",
                             'tool_type':"wikitionary",
                             'created_on':datetime.utcnow(),
                             'created_by':username
                        }
                return render(request, 'wiki_dict_upload.html', {'msg':msg_val,'username_val':username_val,'history_val_dict':history_val_dict})
    history_details = history.objects.all()
    return render(request, 'wiki_dict_upload.html',{'username_val':username_val,'history_val_dict':history_details})


def wiki_commons_file_download(request):
    username_val  = request.session['username']
    img_values = ['https://upload.wikimedia.org/wikipedia/commons/5/52/Belford_Hospital_-_geograph.org.uk_-_2367656.jpg','https://upload.wikimedia.org/wikipedia/commons/a/ab/Calvary_Hospital_at_Hutt_Street%2C_cnr_Wakefield_Street%2C_Adelaide.jpg','https://upload.wikimedia.org/wikipedia/commons/a/ae/Children%27s_Hospital_of_Winnipeg_Complex.jpg','https://upload.wikimedia.org/wikipedia/commons/f/f6/Eidsvold_Hospital%2C_2014.jpg']
    for i in range(len(img_values)):
         print(i)
    return render(request, 'wiki_commons_file_download.html',{'username_val':username_val,'img_links':img_values})
    