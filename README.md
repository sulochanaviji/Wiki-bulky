# Wiki-Bulky --> It is a Django based web tool used to download and upload the bulk files from wikimedia commons and wikitionary.

- Project type - web application
- Language used - Django,Python

### App Features
- It is used to download the bulk files from wikimedia commons by using the category search.
- Used to upload bulk words to wikitionary


### To do list

- Project deployment in tools forge
- Files selection download


### Steps to Execute the App

- Clone this repo
- activate the virtual env
  ```
  ~$ source bulk_downloader/bin/activate
  ```
3.Install the required modules
```
  ~$ pip3 install -r requirements.txt 
 ```
4. Run the migrations
```
  ~$ python3 manage.py makemigrations
  ~$ python3 manage.py migrate
 ```
5. ### Run the Django Server
  ~ python3 manage.py runserver
  







