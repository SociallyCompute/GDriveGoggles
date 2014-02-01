GDriveGoggles
==============
A Python 3.3 GDrive metadata scraper. 

Dependencies
------------
- mysql-connector-python
- requests
- requests-oauthlib

Setup and Installation
----------------------
1. Install Python 3.3 on the computer you use.  Recognize that many standard installations of Python are
   currently 2.x, and you may need to install Python 3.3 as well.  To execute with Python3, you type "python3"
2. Install the dependencies
    1. Make sure you have "pip" installed on your system (this is a package manager for Python3)
    2. From a command prompt, type:
```
pip install mysql-connector-python requests requests-oauthlib
```
3. if pip is not installed, issue these commands:
``` 	 
	wget http://pypi.python.org/packages/source/p/pip/pip-1.1.tar.gz#md5=62a9f08dd5dc69d76734568a6c040508
    	 
	tar -xvf pip*.gz

	cd pip*

	sudo python setup.py install
```
3. Build database
	1. Create empty database
	2. Create new user for db or grant access to an existing user
	3. Run config/schema.sql
4. Set database config options in config/settings.cfg
5. Add your OAuth credentials to the oauth table
	1. Get OAuth credentials by setting up an Application at Googles's Developers site (https://cloud.google.com/console)
	2. Select the App in your google developers console
	3. Choose "Credentials" under "APIs and auth"
	4. Under "Oauth", push the red "CREATE NEW CLIENT ID" button
	5. When Prompted, select "Other"
	6. This will result in a "Client ID for Native Application" being created. 
	7. Populate the "Client ID" and "Client Secret" in the GDriveGoggles oauth table
	8. You then need to go to the command line and follow these steps ... 
		a. python3 ./gdrive-goggles.py 1 
		b. (the result, below, requires you to copy the URL into a browser)
			vvvvv Start: 2014-02-01 17:58:16
			Head: 1
			Delay: 0
			Connecting to database...
			Connected
			+++++ Job ID:2511	Description:test	OAuth ID:2511
			Please go to https://accounts.google.com/o/oauth2/auth?response_type=code&client_id=xxx uri=xxx.readonly&state=xxxe&access_type=offline and authorize access.
			Enter the URL of the page Google redirects you to: 
		c. Somewhat oddly, the browser then redirects you to a "localhost" based URL.  An empty, error page.  This is actually correct.  Just copy the URL and past it back into the terminal response.  From this point forward, this OAUTH will work.
		c.  You will need to follow these steps for each OAUTH you create
 

Usage
-----
```
usage: gdrive-goggles.py [-h] [-v] [-d DELAY] head

positional arguments:
  head                  Specify the head # (zombie_head in the job table)

optional arguments:
  -h, --help            Show this help message and exit
  -v, --verbose         Show additional logs
  -d DELAY, --delay DELAY
                        Delay execution by DELAY seconds
```

Unix Cron Example
-----------------
```
*/1 * * * * /usr/local/bin/python3 /home/gdrive-goggles.py -v -d 2 1 >> ~/log/zombielog-head-1-1.txt
*/1 * * * * /usr/local/bin/python3 /home/gdrive-goggles.py -v -d 17 2 >> ~/log/zombie-head-2-1.txt
*/1 * * * * /usr/local/bin/python3 /home/gdrive-goggles.py -v -d 33 3 >> ~/log/zombielog-head-3-1.txt
*/1 * * * * /usr/local/bin/python3 /home/gdrive-goggles.py -v -d 47 4 >> ~/log/zombielog-head-4-1.txt
```


