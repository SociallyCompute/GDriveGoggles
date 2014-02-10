import argparse, collections, configparser, json, math, mysql.connector as sql, os, requests, sys, time, difflib
from datetime import datetime
from mysql.connector import errorcode
from requests import HTTPError
from requests import ConnectionError
from requests_oauthlib import OAuth2Session, TokenUpdated

# Print strings in verbose mode
def verbose(info) :
	if args.verbose:
		printUTF8(info)

def printUTF8(info) :
	print(info.encode('ascii', 'replace').decode())

# Connect to MySQL using config entries
def connect() :
	config = configparser.ConfigParser()
	script_dir = os.path.dirname(__file__)
	config_file = os.path.join(script_dir, 'config/settings.cfg')
	config.read(config_file)

	db_params = {
		'user' : config["MySQL"]["user"],
		'password' : config["MySQL"]["password"],
		'host' : config["MySQL"]["host"],
		'port' : int(config["MySQL"]["port"]),
		'database' : config["MySQL"]['database'],
		'charset' : 'utf8',
		'collation' : 'utf8_general_ci',
		'buffered' : True
	}

	return sql.connect(**db_params)

# Get all jobs from the database
def getJobs(conn) :
	cursor = conn.cursor() 

	query = ("SELECT job_id, zombie_head, state, from_change_id, folder_id, description, \
				oauth.oauth_id, client_id, client_secret, access_token, refresh_token \
			FROM job, oauth \
			WHERE job.state > 0 AND job.oauth_id = oauth.oauth_id AND zombie_head = %s \
			ORDER BY job_id")

	cursor.execute(query,[args.head])

	return cursor

# Get all files to be watched by a job
def getAndUpdateFilesForJob(conn, client, folder_id) :
	files = set()

	queue = collections.deque()
	queue.append({'id':folder_id})
	while len(queue) > 0:
		next = queue.popleft();
		file_id = next['id']
		file_metadata = getFile(client, next['id'])

		# Update file metadata
		updateFile(conn, file_metadata)
		updateFileOwners(conn, file_metadata)

		if file_metadata['mimeType'] == 'application/vnd.google-apps.folder':
			children = getChildren(client, file_id)
			queue.extendleft(children['items'])
		else :
			files.add(file_id)

	return files

# Get the access token and refresh token for the 
def getInitialAuthorization(client_id, client_secret) :
		redirect_uri = "https://localhost"
		scope = 'https://www.googleapis.com/auth/drive.readonly'

		client = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scope)

		authorization_url, state = client.authorization_url('https://accounts.google.com/o/oauth2/auth', access_type="offline", approval_prompt="force")

		# Require the user to manually authorize the app
		printUTF8('Please go to {} and authorize access.'.format(authorization_url))

		authorization_response = input('Enter the URL of the page Google redirects you to: ')

		# Retrieve the initial oauth token
		token = client.fetch_token('https://accounts.google.com/o/oauth2/token', authorization_response=authorization_response, client_secret=client_secret)

		return client, token

# Store the access token and refresh token
def updateOAuthCredentials(token) :
	global conn, oauth_id, client_id, client_secret

	cursor = conn.cursor()

	query = "UPDATE oauth SET access_token=%s, refresh_token=%s WHERE oauth_id=%s"

	values = [
		token['access_token'],
		token['refresh_token'],
		oauth_id
	]

	try :
		cursor.execute(query, values)
		conn.commit()
	except sql.Error as err :
		verbose(">>>> Warning: Could not update oauth credentials: " + str(err))
		verbose("     Query: " + cursor.statement)
	finally:
		cursor.close()

# Get updated oauth credentials
def getRefreshedAuthorization(client_id, client_secret, access_token, refresh_token) :
	# Construct the token
	token = {
		'access_token': access_token,
		'refresh_token': refresh_token,
		'token_type': 'Bearer',
		'expires_in': -1
	}

	auto_refresh_kwargs = {
		'client_id': client_id,
		'client_secret': client_secret
	}

	client = OAuth2Session(client_id, token=token, auto_refresh_url='https://accounts.google.com/o/oauth2/token', auto_refresh_kwargs=auto_refresh_kwargs, token_updater=updateOAuthCredentials)

	return client

# Get all changes since we last checked
def getChanges(client, start_change_id) :
	max_results = 1000

	fields = [
		'nextPageToken',
		'largestChangeId',
		'items/fileId'
	]

	changes = client.get('https://www.googleapis.com/drive/v2/changes?maxResults={}&fields={}&startChangeId={}'.format(max_results, ','.join(fields), start_change_id))

	return changes.json()

# Get children metadata
def getChildren(client, folder_id) :
	max_results = 1000

	fields = [
		'items/id'
	]

	children = client.get('https://www.googleapis.com/drive/v2/files/{}/children?maxResults={}&fields={}'.format(folder_id, max_results, ','.join(fields)))

	return children.json()

# Get file metadata
def getFile(client, file_id) :
	fields = [
		'id', 
		'title', 
		'mimeType', 
		'description', 
		'createdDate', 
		'modifiedDate', 
		'originalFilename', 
		'fileExtension', 
		'md5Checksum', 
		'fileSize', 
		'ownerNames', 
		'lastModifyingUserName'
	]

	file = client.get('https://www.googleapis.com/drive/v2/files/{}?fields={}'.format(file_id, ','.join(fields)))

	return file.json()

# Update the file
def updateFile(conn, file) :
	cursor = conn.cursor()

	query = "REPLACE INTO file (file_id, title, mime_type, " \
		"description, created_date, modified_date, original_filename, md5, file_extension, file_size, " \
		"last_modifying_user_name) VALUES " \
		"(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
		
	values = [
		file['id'], 
		file['title'], 
		file['mimeType'], 
		file['description'] if "description" in file else "",
		file['createdDate'], 
		file['modifiedDate'], 
		file['originalFilename'] if "originalFilename" in file else "", 
		file['fileExtension'] if "fileExtension" in file else "", 
		file['md5Checksum'] if "md5Checksum" in file else "", 
		file['fileSize'] if "fileSize" in file else -1, 
		file['lastModifyingUserName']
	]

	try :
		cursor.execute(query, values)
		conn.commit()
	except sql.Error as err :
		verbose("")
		verbose(">>>> Warning: Could not upsert file: " + str(err))
		verbose("     Query: " + cursor.statement)
	
	cursor.close()

# Update the file owners
def updateFileOwners(conn, file) :
	cursor = conn.cursor()

	delete_query = "DELETE from file_owners " \
		"WHERE file_id = %s"

	delete_values = [
		file['id']
	]

	try :
		cursor.execute(delete_query, delete_values)
		conn.commit()

	except sql.Error as err :
		verbose("")
		verbose(">>>> Warning: Could not delete old file owners: " + str(err))
		verbose("     Query: " + cursor.statement)

	insert_query = "INSERT INTO file_owners (file_id, owner_name) "\
		"VALUES (%s, %s) "

	for owner in file['ownerNames']:	
		insert_values = [
			file['id'],
			owner
		]

		try :
			cursor.execute(insert_query, insert_values)
			conn.commit()

		except sql.Error as err :
			verbose("")
			verbose(">>>> Warning: Could not insert file owner: " + str(err))
			verbose("     Query: " + cursor.statement)
		
	cursor.close()

# Get all file revisions
def getRevisions(client, file_id) :
	fields = [
		'items/id', 
		'items/mimeType', 
		'items/modifiedDate', 
		'items/lastModifyingUserName', 
		'items/md5Checksum', 
		'items/fileSize',
		'items/exportLinks'
	]

	revisions = client.get('https://www.googleapis.com/drive/v2/files/{}/revisions?fields={}'.format(file_id, ','.join(fields))).json()

	file_contents = None
	file_contents_plaintext = None

	for revision in revisions['items']:
		revision['file_contents'] = None
		revision['file_contents_plaintext'] = None
	
		mime_type = revision['mimeType']
		if (mime_type == 'application/vnd.google-apps.document') :
			revision['file_contents_plaintext'] = client.get(revision['exportLinks']['text/plain']).text
		elif (mime_type == 'application/vnd.google-apps.spreadsheet') :
			revision['file_contents'] = client.get(revision['exportLinks']['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']).content
		elif (mime_type == 'application/vnd.google-apps.presentation') :
			revision['file_contents'] = client.get(revision['exportLinks']['application/vnd.openxmlformats-officedocument.presentationml.presentation']).content
		elif (mime_type == 'application/vnd.google-apps.drawing') :
			revision['file_contents'] = client.get(revision['exportLinks']['image/png']).content

	return revisions

# Populate revision diffs
def populateRevisionDiffs(revisions) :
	previous = ''
	for revision in sorted(revisions['items'], key = lambda revision : int(revision['id']) ) :
		if (revision['file_contents_plaintext'] is not None) :
			current = revision['file_contents_plaintext']
			revision['file_contents_plaintext_diff'] = ''.join(difflib.unified_diff(previous.splitlines(1), current.splitlines(1)))
			previous = current
		else :
			revision['file_contents_plaintext_diff'] = None

# Add all revisions to the DB
def addRevisions(conn, client, file_id, revisions) :
	cursor = conn.cursor()

	query = "INSERT INTO revision (file_id, revision_id, mime_type, modified_date, last_modifying_user_name, md5, file_size, file_contents, file_contents_plaintext, file_contents_plaintext_diff) " \
		"VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)  ON DUPLICATE KEY UPDATE revision_id=revision_id"

	for revision in revisions['items']:
		values = [
			file_id, 
			revision['id'], 
			revision['mimeType'], 
			revision['modifiedDate'], 
			revision['lastModifyingUserName'] if "lastModifyingUserName" in revision else "anonymous", 
			revision['md5Checksum'] if "md5Checksum" in revision else "", 
			revision['fileSize'] if "fileSize" in revision else -1,
			revision['file_contents'],
			revision['file_contents_plaintext'],
			revision['file_contents_plaintext_diff']
		]

		try :
			cursor.execute(query, values)
			conn.commit()
		except sql.Error as err :
			verbose("")
			verbose(">>>> Warning: Could not add revision: " + str(err))
			verbose("     Query: " + cursor.statement)
	
	cursor.close()

# Get all file comments
def getComments(client, file_id) :
	max_results = 100

	fields = [
		'items/commentId', 
		'items/createdDate', 
		'items/modifiedDate', 
		'items/author/displayName', 
		'items/content', 
		'items/status', 
		'items/replies/replyId', 
		'items/replies/createdDate', 
		'items/replies/modifiedDate', 
		'items/replies/author/displayName', 
		'items/replies/content'
	]

	comments = client.get('https://www.googleapis.com/drive/v2/files/{}/comments?maxResults={}&fields={}'.format(file_id, max_results, ','.join(fields)))

	return comments.json()

# Add all comments to the DB
def addComments(conn, file_id, comments) :
	cursor = conn.cursor()

	query = "REPLACE INTO comment (file_id, comment_id, created_date, modified_date, author, content, status) " \
		"VALUES(%s, %s, %s, %s, %s, %s, %s) "

	for comment in comments['items']:
		values = [
			file_id, 
			comment['commentId'], 
			comment['createdDate'], 
			comment['modifiedDate'], 
			comment['author']['displayName'], 
			comment['content'], 
			comment['status']
		]

		try :
			cursor.execute(query, values)
			conn.commit()
		except sql.Error as err :
			verbose("")
			verbose(">>>> Warning: Could not add comments: " + str(err))
			verbose("     Query: " + cursor.statement)
	
	cursor.close()

# Add all comment replies to the DB
def addReplies(conn, file_id, comments) :
	cursor = conn.cursor()

	query = "REPLACE INTO reply (file_id, comment_id, reply_id, created_date, modified_date, author, content) " \
		"VALUES(%s, %s, %s, %s, %s, %s, %s) "

	for comment in comments['items']:
		for reply in comment['replies']:
			values = [
				file_id, 
				comment['commentId'], 
				reply['replyId'], 
				reply['createdDate'], 
				reply['modifiedDate'], 
				reply['author']['displayName'],
				reply['content']
			]

			try :
				cursor.execute(query, values)
				conn.commit()
			except sql.Error as err :
				verbose("")
				verbose(">>>> Warning: Could not add replies: " + str(err))
				verbose("     Query: " + cursor.statement)
		
	cursor.close()

# Update job status
def updateJob(conn, job_id, from_change_id) :
	cursor = conn.cursor()

	query = "UPDATE job SET from_change_id=%s, last_run=%s WHERE job_id=%s"

	values = [
		str(int(from_change_id) + 1),
		datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
		job_id
	]

	try :
		cursor.execute(query, values)
		conn.commit()
	except sql.Error as err :
		verbose(">>>> Warning: Could not update job: " + str(err))
		verbose("     Query: " + cursor.statement)
	finally:
		cursor.close()

# Main function
if __name__ == '__main__' :
	# Handle command line arguments
	parser = argparse.ArgumentParser(description="A Python 3.3 Google Drive scraper")
	parser.add_argument('head', type=int, help="Specify the head #")
	parser.add_argument('-v','--verbose', default=False, action="store_true", help="Show additional logs")
	parser.add_argument('-d','--delay', type=int, default=0, help="Delay execution by DELAY seconds")
	args = parser.parse_args()

	# Display startup info
	print("vvvvv Start:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
	verbose("Verbose Mode: Enabled")
	print("Head:", args.head)
	print("Delay:", args.delay)

	epoch_min = math.floor(time.time() / 60)
	verbose("Epoch Minutes: " + str(epoch_min))

	if (args.delay > 0) :
		time.sleep(args.delay)

	print("Connecting to database...")

	try :
		run_total_count = 0
		conn = connect()
		print("Connected")

		# Get all of the jobs for this head
		jobs = getJobs(conn)

		if not jobs.rowcount :
			print("\nUnable to find any jobs to run. Please make sure there are entries in the 'job'"
				+ " table that have an oauth_id corresponding to an entry in the 'oauth', the 'zombie_head'"
				+ " value matches {}, and the 'state' value is greater than 0.\n".format(args.head))

		# Iterate over all of the jobs found
		for (job_id, zombie_head, state, from_change_id, folder_id, description, oauth_id, client_id, client_secret, access_token, refresh_token) in jobs :

			# Throttle the job frequency
			if (epoch_min % state != 0) :
				verbose("Throttled frequency for job: " + str(job_id))
				continue
			
			printUTF8("+++++ Job ID:" + str(job_id) + "\tDescription:" + description + "\tOAuth ID:" + str(oauth_id))

			# Perform first time authorization
			if access_token is None or refresh_token is None :
				# Get the proper authorization from the user. Note that this requires manual input.
				client, token = getInitialAuthorization(client_id, client_secret)

				# Save the access token and refresh token
				updateOAuthCredentials(token)

			# Perform subsequent authorizations
			else :
				client = getRefreshedAuthorization(client_id, client_secret, access_token, refresh_token)
			
			# Get a set of files we care about
			files = getAndUpdateFilesForJob(conn, client, folder_id)

			# Get a list of all changes since we last looked
			changes = getChanges(client, from_change_id)

			# Iterate over all of the changes, seeing if any are on files we care about
			for change in changes['items'] :
				file_id = change['fileId']
				if file_id in files :
					# Get all of the revisions for a file that has changed
					revisions = getRevisions(client, file_id)
					populateRevisionDiffs(revisions)
					addRevisions(conn, client, file_id, revisions)

					# Update comments
					comments = getComments(client, file_id)
					addComments(conn, file_id, comments)
					addReplies(conn, file_id, comments)

					run_total_count = run_total_count + 1

			updateJob(conn, job_id, changes['largestChangeId'])

	except sql.Error as err :
		print(err)
		print("Terminating.")
		sys.exit(1)
	else :
		conn.close()
	finally :
		print("$$$$$ Updated file count: " + str(run_total_count))
		print("^^^^^ Stop:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
